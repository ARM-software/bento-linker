import toml
import sys
import os.path
import collections as co
import itertools as it
from .box import Box
from .box import System
from .argstuff import ArgumentParser

COMMANDS = co.OrderedDict()
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
        sys_ = System(**args)
        sys_.box()

        def ls(box):
            print('sys' if box.issys() else 'box %s' % box.name)
            print('  %(name)-34s %(path)s' % dict(
                name='path', path=box.path))
            if not box.issys():
                print('  %(name)-34s %(runtime)s' % dict(
                    name='runtime', runtime=box.runtime.__argname__))
            for memory in box.memories:
                print('  %(name)-34s %(memory)s' % dict(
                    name='memories.%s' % memory.name, memory=memory))
            if box.imports:
                print('  imports')
                for import_ in box.imports:
                    print('    %(name)-32s %(import_)s' % dict(
                        name=import_.name, import_=import_))
            if box.exports:
                print('   exports')
                for export in box.exports:
                    print('    %(name)-32s %(export)s' % dict(
                        name=export.name, export=export))

            for box in box.boxes:
                ls(box)

        ls(sys_)

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
        print("parsing...")
        sys_ = System(**args)

        print("building...")
        sys_.box()
        sys_.build()

        for box in it.chain(sys_.boxes, [sys_]):
            for name, output in box.outputs.items():
                print("writing %s %s %s..." % (
                    box.name or 'sys', name, output.path))
                with open(output.path, 'w') as outf:
                    # TODO open in Output.__init__?
                    outf.write(output.getvalue())

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
