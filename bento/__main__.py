import toml
import sys
import os.path
import collections as c
from .box import Box
from .box import System
from .argstuff import ArgumentParser

COMMANDS = c.OrderedDict()
def command(cls):
    assert cls.__argname__ not in COMMANDS
    COMMANDS[cls.__argname__] = cls
    return cls

@command
class ListCommand:
    """
    List the setup of boxes as sepcified by the current configuration.
    """
    __argname__ = "ls"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser):
        System.__argparse__(parser)
    def __init__(self, **args):
        sys = System(**args)
        sys.ls()
        for box in sys.boxes:
            box.ls()

@command
class BuildCommand:
    """
    Build the ingredients for a box as specified by the "output"
    configurations.
    """
    __argname__ = "build"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser):
        System.__argparse__(parser)
    def __init__(self, **args):
        sys_ = System(**args)
            
        for box in sys_.boxes:
            for name, (path, output) in sorted(box.outputs.items()):
                print("building %s %s %s..." % (box.name, name, path))
                if hasattr(box.runtime, 'build_box_%s' %
                        name.replace('-', '_')):
                    builder = output(sys_, box, path)
                    getattr(box.runtime, 'build_box_%s' %
                            name.replace('-', '_'))( # TODO rm this replace? handle elsewhere?
                        sys_, box, builder)
                    with open(path, 'w') as outf:
                        builder.build(outf)
                else:
                    print("%s: error: runtime %s "
                        "doesn't know how to output \"%s\"" % (
                        os.path.basename(sys.argv[0]),
                        box.runtime.__argname__,
                        name), file=sys.stderr)
                    raise SystemExit(3)

        for name, (path, output) in sorted(sys_.outputs.items()):
            print("building %s %s..." % (name, path))
            builder = output(sys_, box)
            touched = False

            runtimes = {}
            for box in sys_.boxes:
                runtimes[box.runtime.__argname__] = box.runtime

            for runtime in runtimes:
                if hasattr(box.runtime, 'build_sys_%s_prologue' %
                        name.replace('-', '_')):
                    with builder.pushattrs():
                        getattr(box.runtime, 'build_sys_%s_prologue' %
                                name.replace('-', '_'))(
                            sys_, builder)
                    touched = True

            for box in sys_.boxes:
                if hasattr(box.runtime, 'build_sys_%s' %
                        name.replace('-', '_')):
                    with builder.pushattrs(box=box.name, BOX=box.name.upper()):
                        getattr(box.runtime, 'build_sys_%s' %
                                name.replace('-', '_'))(
                            sys_, box, builder)
                    touched = True

            for runtime in runtimes:
                if hasattr(box.runtime, 'build_sys_%s_epilogue' %
                        name.replace('-', '_')):
                    with builder.pushattrs():
                        getattr(box.runtime, 'build_sys_%s_epilogue' %
                                name.replace('-', '_'))(
                            sys_, builder)
                    touched = True

            if not touched:
                print("%s: error: runtimes {%s} "
                    "doesn't know how to output \"%s\"" % (
                    os.path.basename(sys.argv[0]),
                    ', '.join(box.runtime.__argname__
                        for box in sys_.boxes),
                    name), file=sys.stderr)
                raise SystemExit(3)

            with open(path, 'w') as outf:
                builder.build(outf)
                    
        print("done!")

def main():
    parser = ArgumentParser(
        description="A tool for building compile time files for "
            "connecting bento-boxes.")
    subparsers = parser.add_subparsers(title="subcommand", dest="command",
        help="Command to run.")
    for name, command in COMMANDS.items():
        subparser = subparsers.add_parser(name, help=command.__arghelp__)
        subparser.set_defaults(command=command)
        command.__argparse__(subparser)

    args = parser.parse_args()
    if not args.command:
        parser.parse_args(['-h'])
    args.command(**args.__dict__)
    sys.exit(0)

if __name__ == "__main__":
    main()
