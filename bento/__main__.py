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
    def __init__(self, args):
        sys = System(args)
        sys.ls()
        for box in sys.boxes.values():
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
    def __init__(self, args):
        sys_ = System(args)
            
        for box in sys_.boxes.values():
            for outname, output in sorted(box.outputs.items()):
                print("building %s %s %s..." % (box.name, outname, output.path))
                if hasattr(box.runtime, 'build_box_%s' % outname):
                    getattr(box.runtime, 'build_box_%s' % outname)(
                        sys_, box, output)
                    with open(output.path, 'w') as outf:
                        output.build(sys_, box, outf)
                else:
                    print("%s: error: runtime %s "
                        "doesn't know how to output \"%s\"" % (
                        os.path.basename(sys.argv[0]),
                        box.runtime.__argname__,
                        outname), file=sys.stderr)
                    raise SystemExit(3)

        for outname, output in sorted(sys_.outputs.items()):
            print("building %s %s..." % (outname, output.path))
            touched = False

            runtimes = {}
            for box in sys_.boxes.values():
                runtimes[box.runtime.__argname__] = box.runtime

            for runtime in runtimes:
                if hasattr(box.runtime, 'build_sys_%s_prologue' % outname):
                    getattr(box.runtime, 'build_sys_%s_prologue' % outname)(
                        sys_, output)
                    touched = True

            for box in sys_.boxes.values():
                if hasattr(box.runtime, 'build_sys_%s' % outname):
                    getattr(box.runtime, 'build_sys_%s' % outname)(
                        sys_, box, output)
                    touched = True

            for runtime in runtimes:
                if hasattr(box.runtime, 'build_sys_%s_epilogue' % outname):
                    getattr(box.runtime, 'build_sys_%s_epilogue' % outname)(
                        sys_, output)
                    touched = True

            if not touched:
                print("%s: error: runtimes {%s} "
                    "doesn't know how to output \"%s\"" % (
                    os.path.basename(sys.argv[0]),
                    ', '.join(box.runtime.__argname__
                        for box in sys_.boxes.values()),
                    outname), file=sys.stderr)
                raise SystemExit(3)

            with open(output.path, 'w') as outf:
                output.build(sys_, None, outf)
                    
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
    args.command(args)
    sys.exit(0)

if __name__ == "__main__":
    main()
