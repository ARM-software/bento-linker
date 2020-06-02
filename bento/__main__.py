import toml
import sys
import os.path
import collections as co
import itertools as it
from .box import Box
from .argstuff import ArgumentParser

COMMANDS = co.OrderedDict()
def command(cls):
    assert cls.__argname__ not in COMMANDS
    COMMANDS[cls.__argname__] = cls
    return cls

@command
class ListCommand:
    """
    List the setup of boxes as specified by the current configuration.
    """
    __argname__ = "ls"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser):
        parser.add_argument('-a', action='store_true',
            help='Also show implicit exports/imports used for runtime '
                'plumbing.')
        parser.add_argument('-n', '--no_check', action='store_true',
            help='Don\'t perform memory allocation and linking. This '
                'shows less info, but may be helpful for debugging bad '
                'configuration.')
        Box.scan.__argparse__(parser)
    def __init__(self, a=False, no_check=False, **args):
        box = Box.scan(**args)
        if not no_check:
            box.box()
            box.link()

        def ls(box):
            print('box %s' % box.name)
            print('  %(name)-34s %(path)s' % dict(
                name='path', path=box.path))
            print('  %(name)-34s %(runtime)s' % dict(
                name='runtime', runtime=box.runtime.__argname__))
            for memory in box.memories:
                print('  %(name)-34s %(memory)s' % dict(
                    name='memories.%s' % memory.name, memory=memory))
            for i, import_ in enumerate(
                    import_ for import_ in box.imports
                    if a or getattr(import_, 'source', box) == box) :
                if i == 0:
                    print('  imports')
                print('    %(name)-32s %(import_)s' % dict(
                    name=import_.name, import_=import_))
            for i, export in enumerate(
                    export for export in box.exports
                    if a or getattr(export, 'source', box) == box):
                if i == 0:
                    print('  exports')
                print('    %(name)-32s %(export)s' % dict(
                    name=export.name, export=export))

            for box in box.boxes:
                ls(box)

        ls(box)

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
        Box.scan.__argparse__(parser)
    def __init__(self, **args):
        print("scanning...")
        box = Box.scan(**args)
        box.box()
        box.link()

        def stackwarn(box):
            if not box.stack.size:
                print("%s: warning: box %s has no stack!" % (
                    os.path.basename(sys.argv[0]), box.name))
            for child in box.boxes:
                stackwarn(child)
        stackwarn(box)
        sys_ = box

        print("building...")
        box.build()

        def outputwrite(box):
            for output in box.outputs:
                print("writing %s %s %s > %s..." % (
                    box.name, box.runtime.name, output.name, output.path))
                with open(output.path, 'w') as outf:
                    # TODO open in Output.__init__?
                    outf.write(output.getvalue())
            for child in box.boxes:
                outputwrite(child)
        outputwrite(box)
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
    args.command(**{
        k: v for k, v in args.__dict__.items()
        if k != 'command'})
    sys.exit(0)

if __name__ == "__main__":
    main()
