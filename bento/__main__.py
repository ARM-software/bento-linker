import sys
import os.path
import collections as co
import itertools as it
import textwrap
import re
from .box import Box
from .argstuff import ArgumentParser
from .glue.error_glue import ErrorGlue

COMMANDS = co.OrderedDict()
def command(cls):
    assert cls.__argname__ not in COMMANDS
    COMMANDS[cls.__argname__] = cls
    return cls

def box_argparse(cls, parser):
    # Show the most useful options, but omit most of these as the
    # help text becomes unwieldy
    parser.add_argument('--path PATH', fake=True,
        help="Working directory for the box. Defaults to the current "
            "directory.")
    parser.add_argument('--recipe RECIPE', fake=True,
        help="Path to reciple.toml file for box-specific configuration. "
            "Defaults to <path>/recipe.toml.")
    parser.add_glob(Box.scan,
        help="This command also accepts all box configuration options. "
            "Run '%s options' for a full list."
            % os.path.basename(sys.argv[0]))

@command
class BoxesCommand:
    """
    List the boxes as specified by the current configuration.
    """
    __argname__ = "boxes"
    __arghelp__ = __doc__
    __argaliases__ = ["ls"]
    @classmethod
    def __argparse__(cls, parser):
        parser.add_argument('-p', action='store_true',
            help="Also show implicit plumbing exports/imports.")
        parser.add_argument('-B', '--no-box', action='store_true',
            help="Don't perform memory/section allocation or linking. This"
                "shows less info, but may be helpful for debugging "
                "configurations that fail during boxing.")
        parser.add_argument('-L', '--no-link', action='store_true',
            help="Don't perform the box-level linking. This"
                "shows less info, but may be helpful for debugging "
                "configurations that fail during linking.")
        box_argparse(cls, parser)
    def __init__(self, p=False, no_box=False, no_link=False, **args):
        box = Box.scan(**args)
        if not no_box:
            box.box()
        if not no_box and not no_link:
            box.link()

        def ls(box):
            print('box %s' % box.name)
            print('  %(name)-34s %(path)s' % dict(
                name='path', path=box.path))
            print('  %(name)-34s %(runtime)s' % dict(
                name='runtime', runtime=box.runtime.__argname__))
            print('  %(name)-34s %(loader)s' % dict(
                name='loader', loader=box.loader.__argname__))
            for memory in box.memories:
                print('  %(name)-34s %(memory)s' % dict(
                    name='memory.%s' % memory.name, memory=memory))
            for i, import_ in enumerate(
                    import_ for import_ in box.imports
                    if p or import_.source == box.name
                    if import_.link):
                if i == 0:
                    print('  import')
                print('    %(name)-32s %(import_)s' % dict(
                    name=import_.scopedname, import_=import_))
            for i, export in enumerate(
                    export for export in box.exports
                    if p or export.source == box.name):
                if i == 0:
                    print('  export')
                print('    %(name)-32s %(export)s' % dict(
                    name=export.scopedname, export=export))

            for box in box.boxes:
                ls(box)

        ls(box)

@command
class LinksCommand:
    """
    List the import/export links as specified by the current configuration.
    """
    __argname__ = "links"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser):
        parser.add_argument('-p', action='store_true',
            help="Also show implicit plumbing exports/imports.")
        box_argparse(cls, parser)
    def __init__(self, p=False, **args):
        box = Box.scan(**args)
        box.box()
        box.link()

        def links(box):
            for i, export in enumerate(
                    export for export in box.exports
                    if p or export.source == box.name):
                if i == 0:
                    print('box %s' % box.name)
                exportname = (
                    '%s.export.%s' % (export.source, export.scopedname)
                    if export.source != box.name else
                    'export.%s' % export.scopedname)
                if len(exportname) > 32 and any(
                        link.import_ for link in export.links):
                    print('  %s' % exportname)
                for j, import_ in enumerate(
                        link.import_ for link in export.links):
                    print('  %(export)-32s -> %(import_)s' % dict(
                        export=exportname
                            if j == 0 and len(exportname) <= 32 else '',
                        import_='%s.import.%s' % (
                            import_.source, import_.name)))

            for box in box.boxes:
                links(box)

        links(box)

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
        box_argparse(cls, parser)
    def __init__(self, **args):
        box = Box.scan(**args)
        box.box()
        box.link()
        box.build()

        def outputwrite(box):
            for output in box.outputs:
                print('generating %(name)s(%(runtime)s%(loader)s+%(output)s) '
                    '%(path)s' % dict(
                        name=box.name,
                        runtime=box.runtime.name,
                        loader=('+'+box.loader.name
                            if box.loader.name != 'noop' else
                            ''),
                        output=output.name,
                        path=output.path))
                with open(output.path, 'w') as outf:
                    # TODO open in Output.__init__?
                    outf.write(output.getvalue())
            for child in box.boxes:
                outputwrite(child)
        outputwrite(box)

@command
class OptionsCommand:
    """
    List the configuration options available for boxes. These can be
    provided on the command-line or specified in a recipe.toml file.
    """
    __argname__ = "options"
    __arghelp__ = __doc__
    def __init__(self):
        parser = ArgumentParser()
        Box.scan.__argparse__(parser)
        parser.parse_args(['-h'])

@command
class RuntimesCommand:
    """
    List the available runtimes and their help text.
    """
    __argname__ = "runtimes"
    __arghelp__ = __doc__
    def __init__(self):
        from .runtimes import RUNTIMES
        print("available runtimes:")
        for Runtime in RUNTIMES.values():
            if len(Runtime.__argname__) > 19:
                print(4*' '+Runtime.__argname__)
            for i, line in enumerate(textwrap.wrap(
                    re.sub(r'\s+', ' ', Runtime.__arghelp__.strip()),
                    width=78-24)):
                print(4*' '+'%(name)-19s %(line)s' % dict(
                    name=Runtime.__argname__
                        if len(Runtime.__argname__) <= 19 and i == 0 else
                        '',
                    line=line))

@command
class LoadersCommand:
    """
    List the available loaders and their help text.
    """
    __argname__ = "loaders"
    __arghelp__ = __doc__
    def __init__(self):
        from .loaders import LOADERS
        print("available loaders:")
        for Loader in LOADERS.values():
            if len(Loader.__argname__) > 19:
                print(4*' '+Loader.__argname__)
            for i, line in enumerate(textwrap.wrap(
                    re.sub(r'\s+', ' ', Loader.__arghelp__.strip()),
                    width=78-24)):
                print(4*' '+'%(name)-19s %(line)s' % dict(
                    name=Loader.__argname__
                        if len(Loader.__argname__) <= 19 and i == 0 else
                        '',
                    line=line))

@command
class OutputsCommand:
    """
    List the available outputs and their help text.
    """
    __argname__ = "outputs"
    __arghelp__ = __doc__
    def __init__(self):
        from .outputs import OUTPUTS
        print("available outputs:")
        for Output in OUTPUTS.values():
            if len(Output.__argname__) > 19:
                print(4*' '+Output.__argname__)
            for i, line in enumerate(textwrap.wrap(
                    re.sub(r'\s+', ' ', Output.__arghelp__.strip()),
                    width=78-24)):
                print(4*' '+'%(name)-19s %(line)s' % dict(
                    name=Output.__argname__
                        if len(Output.__argname__) <= 19 and i == 0 else
                        '',
                    line=line))

@command
class HooksCommand:
    """
    List the hooks available for boxes. These are implicit runtime-specific
    imports that boxes can connect with box-specific exports.
    """
    __argname__ = "hooks"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser):
        box_argparse(cls, parser)
    def __init__(self, **args):
        box = Box.scan(**args)
        box.box()

        def hooks(box):
            runtimes = {}
            for import_ in box.imports:
                if import_.scope == box.name and import_.source != box.name:
                    if import_.source not in runtimes:
                        runtimes[import_.source] = []
                    runtimes[import_.source].append(import_)

            print('available hooks in %s:' % box.name)
            for runtime, imports in sorted(runtimes.items(),
                    key=lambda r: '' if r[0] == box.runtime else r[0]):
                needsnl = False
                print('  %s hooks:' % runtime)
                for import_ in imports:
                    needsnl = True
                    print('    %(name)-32s %(import_)s' % dict(
                        name=import_.name,
                        import_=import_))
                    if import_.doc:
                        for line in textwrap.wrap(import_.doc, width=78-8):
                            print(8*' ' + line)
                        print()
                        needsnl = False

                if needsnl:
                    print()

            for child in box.boxes:
                hooks(child)

        hooks(box)

@command
class ErrorsCommand:
    """
    List or look up error codes based on name or number.
    """
    __argname__ = "errors"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser):
        parser.add_argument("error", nargs='?',
            help="Error code to look up, either by name or by number.")
    def __init__(self, error):
        if error is None:
            namew, codew = 0, 0
            for name, code, desc in ErrorGlue.errors():
                if len(name) > namew:
                    namew = len(name)
                if len(str(code)) > codew:
                    codew = len(str(code))
            for name, code, desc in ErrorGlue.errors():
                print('%-*s  %*d  %s' % (namew, name, codew, code, desc))
        else:
            try:
                error = int(error, 0)
            except ValueError:
                pass

            found = ErrorGlue.geterror(error)
            if found is None:
                print('Unknown error')
                sys.exit(1)

            name, code, desc = found
            print('%s %s %s' % (name, code, desc))


def main():
    parser = ArgumentParser(
        description="A tool for building compile time files for "
            "connecting bento-boxes.")
    subparsers = parser.add_subparsers(title="subcommand", dest="command",
        help="Command to run.")
    for name, command in COMMANDS.items():
        subparser = subparsers.add_parser(name,
            help=getattr(command, '__arghelp__', None),
            aliases=getattr(command, '__argaliases__', []))
        subparser.set_defaults(command=command)
        if hasattr(command, '__argparse__'):
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
