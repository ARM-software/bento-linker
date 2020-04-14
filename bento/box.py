
import re
import collections as c
from . import argstuff
from .argstuff import ArgumentParser

class Memory:
    """
    Description of a memory region named MEMORY.
    """
    __argname__ = "memory"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser):
        parser.add_argument("--mode", type=cls.parsemode,
            help="String of characters indicating how the underlying memory "
                "can be accessed. Can be a combination of %s." %
                ', '.join(map(repr, cls.MODEFLAGS)))
        parser.add_argument("--start", type=lambda x: int(x, 0),
            help="Starting address of memory region. Note that start may be "
                "undefined if the exact location does not matter.")
        parser.add_argument("--size", type=lambda x: int(x, 0),
            help="Size of memory region in bytes.")
        parser.add_argument("--align", type=lambda x: int(x, 0),
            help="Minimum alignment of the memory region. Used for sanity "
                "check but otherwise unused unless start is not specified.")
        parser.add_argument("--sections", type=cls.parsesections,
            help="List of sections to place in this memory region. If not "
                "specified, %%(prog)s will try to place sections in the "
                "largest compatible memory region.")

    MODEFLAGS = c.OrderedDict([
        ('r', "read"),
        ('w', "write"),
        ('x', "execute")])
    @staticmethod
    def parsemode(s):
        flags = set()
        for c in s:
            if c not in Memory.MODEFLAGS:
                raise ValueError("invalid memory mode %r" % s)
            flags.add(c)
        return flags

#    SECTIONS = c.OrderedDict([
#        ('rom', "Meta-section containing all readonly sections. This is the "
#            "combination of the read-only sections and the init copy of the "
#            "data section."),
#        ('ram', "Meta-section containing all read/write sections. This is the "
#            "combination of the bss, data, stack, and heap sections."),
#        ('text', "Text section "
#            "containing executable code."),
#        ('rodata', "RO Data section "
#            "containing read-only data."),
#        ('bss', "BSS section "
#            "containing read/write data that is zero-initialized."),
#        ('data', "Data section "
#            "containing read/write data with initialization."),
#        ('stack', "Stack section "
#            "containing the stack for execution."),
#        ('heap', "Heap section "
#            "containing the heap for execution.")])
    @staticmethod
    def parsesections(s):
        sections = s.split()
#        for section in sections:
#            if section not in Memory.SECTIONS:
#                raise ValueError("invalid section %r" % section)
        return sections

    def __init__(self, name, args):
        if args.align is not None:
            if args.start is not None:
                assert args.start % args.align == 0, (
                    "memory region not aligned to section alignment "
                    "%#x %% %#x != 0" % (
                        args.start, args.align))
            if args.size is not None:
                assert args.size % args.align == 0, (
                    "memory region not aligned to section alignment "
                    "%#x %% %#x != 0" % (
                        args.size, args.align))

        self.name = name
        self.mode = args.mode or ''
        self.start = args.start
        self.size = args.size or 0
        self.align = args.align
        self.sections = args.sections

    def ls(self):
        """Show configuration on CLI."""
        print("    %-32s %s%s %d bytes%s" % (
            self.name,
            ''.join(c if c in self.mode else '-'
                for c in Memory.MODEFLAGS),
            ' %#010x-%#010x' % (self.start, self.start+self.size-1)
                if self.start else
            ' %#010x' % self.size,
            self.size,
            ' %s align' % self.align if self.align is not None else ''))

class Section:
    """
    Description of a linking section named SECTION.
    """
    __argname__ = "section"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser):
        parser.add_argument("--size", type=lambda x: int(x, 0),
            help="Minimum size of the section.")
        parser.add_argument("--align", type=lambda x: int(x, 0),
            help="Minimum alignment of the section. Defaults to 8 bytes for "
                "stack/heap, 4 bytes otherwise")
#        parser.add_argument("--memory",
#            help="Explicitly state which memory region to place section in. "
#                "If not specified, the sections specified in each memory "
#                "region will be used.")

    def __init__(self, name, args):
        #assert name in Memory.SECTIONS
        if args.align is not None and args.size is not None:
            assert args.size % args.align == 0, (
                "section size not aligned to section alignment "
                "%#x %% %#x != 0" % (
                    args.size, args.align))

        self.name = name
        self.size = args.size or 0
        self.align = args.align
        self.memory = None
#        self.align = args.align or (8 if name in ['stack', 'heap'] else 4)
#        self.memory = args.memory
#
#    def __bool__(self):
#        return self.size is not None

    def ls(self):
        """Show configuration on CLI."""
        # TODO print memory here?
        print("    %-32s %#010x %s bytes%s%s" % (
            self.name,
            self.size,
            self.size,
            ' %s align' % self.align if self.align is not None else '',
            ' in %s' % self.memory.name if self.memory is not None else ''))

class Import:
    """
    Description of an imported function for a box.
    """
    __argname__ = "import"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser):
        parser.add_argument("type", type=cls.parse,
            help=cls.__arghelp__)

    @staticmethod
    def parse(s):
        namepattern = r'[a-zA-Z_][a-zA-Z_0-9]*'
        typepattern = r'%(name)s(?:\s*[\*\&])*' % dict(name=namepattern)
        # three arg permutations: tpye, name: type, type name
        argpattern = (r'(?:'
                r'(%(type)s)|'
                r'(%(name)s):\s*(%(type)s)|'
                r'(%(type)s)\s*(%(name)s)'
            r')' % dict(name=namepattern, type=typepattern))
        # functions with and without parens around args/rets
        fnpattern = (r'\s*fn\s*(?:'
                r'\(\s*((?:%(arg)s(?:\s*,\s*%(arg)s)*)?)\s*\)|'
                r'((?:%(arg)s(?:\s*,\s*%(arg)s)*)?)'
            r')\s*->\s*(?:'
                r'\(\s*((?:%(arg)s(?:\s*,\s*%(arg)s)*)?)\s*\)|'
                r'((?:%(arg)s(?:\s*,\s*%(arg)s)*)?)'
            r')\s*' % dict(arg=argpattern))

        m = re.match('^%s$' % fnpattern, s)
        if not m:
            raise ValueError("Invalid import/export type %r" % s)

        rawargs = (m.group(1) or m.group(12) or '').split(',')
        rawrets = (m.group(23) or m.group(34) or '').split(',') # 35?

        args = []
        for arg in rawargs:
            if arg:
                m = re.match('^%s$' % argpattern, arg.strip())
                name = m.group(2) or m.group(5)
                type = (m.group(1) or m.group(3) or m.group(4)).replace(' ', '')
                args.append(type)
        if args == ['void']:
            args = []

        rets = []
        for ret in rawrets:
            if ret:
                m = re.match('^%s$' % argpattern, ret.strip())
                name = m.group(2) or m.group(5)
                type = (m.group(1) or m.group(3) or m.group(4)).replace(' ', '')
                rets.append(type)
        if rets == ['void']:
            rets = []

        return (args, rets)

    def __init__(self, name, args):
        self.name = name
        self.args, self.rets = args.type

    def ls(self):
        """Show configuration on CLI."""
        print("    %-32s fn(%s) -> %s" % (
            self.name, ', '.join(self.args), ', '.join(self.rets)))

class Export(Import):
    """
    Description of an exported function for a box.
    """
    __argname__ = "export"
    __arghelp__ = __doc__

class Box:
    """
    Descriptton of a given box named BOX.
    """
    __argname__ = "box"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser):
        from .runtimes import RUNTIMES
        parser.add_argument("--runtime", choices=RUNTIMES,
            help="Runtime for the box. This can be one of the following "
                "runtimes: {%(choices)s}.")
        parser.add_argument("--path",
            help="Working directory for the box, defaults to the "
                "name of the box.")

        from .outputs import OUTPUTS
        outputparser = parser.add_nestedparser("--output")
        for output in OUTPUTS['box'].values():
            outputparser.add_argument('--'+output.__argname__,
                help=output.__arghelp__)

#        sectionparser = parser.add_nestedparser("--section")
#        for section, help in Memory.SECTIONS.items():
#            Section.__argparse__(
#                sectionparser.add_nestedparser('--'+section, help=help))
        Memory.__argparse__(
            parser.add_set('--'+Memory.__argname__))
        Section.__argparse__(
            parser.add_set('--'+Section.__argname__))
        Import.__argparse__(
            parser.add_set('--'+Import.__argname__))
        Export.__argparse__(
            parser.add_set('--'+Export.__argname__))

    def __init__(self, name, args):
        self.name = name
        self.path = args.path or name

        # Load additional config from the filesystem
        try:
            parser = ArgumentParser(add_help=False)
            self.__class__.__argparse__(parser)
            nargs = parser.parse_toml(self.path + '/recipe.toml')
            args = argstuff.merge(args, nargs)
        except FileNotFoundError:
            pass

        from .runtimes import RUNTIMES
        from .outputs import OUTPUTS
        self.runtime = RUNTIMES[args.runtime or 'noop']()
        self.outputs = {k: OUTPUTS['box'][k](self.path + '/' + v)
            for k, v in args.output.__dict__.items()
            if v}
        self.memories = {name: Memory(name, memargs)
            for name, memargs in args.memory.items()}
        self.sections = {name: Section(name, sectionargs)
            for name, sectionargs in args.section.items()}
#        for section, help in Memory.SECTIONS.items():
#            Section.__argparse__(
#                parser.add_nestedparser('--'+section, help=help))
#        self.sections = {name: Section(name, sectionargs)
#            for name, sectionargs in args.section.__dict__.items()}
        self.imports = {name: Import(name, importargs)
            for name, importargs in args.__dict__['import'].items()}
        self.exports = {name: Import(name, exportargs)
            for name, exportargs in args.export.items()}

    def ls(self):
        """Show configuration on CLI."""
        print("box %s" % self.name)
        print("  runtime")
        print("    %s" % self.runtime.__argname__)
        if self.outputs:
            print("  outputs")
            for name, output in sorted(self.outputs.items()):
                print("    %-32s %s" % (name, output.path))
#        if self.sections:
#            print("  sections")
#            for name, section in sorted(self.sections.items(),
#                    key=lambda x: ({k: i for i, k in enumerate(
#                        Memory.SECTIONS.keys())})[x[0]]):
#                if section.size is not None:
#                    section.ls()
        if self.memories:
            print("  memories")
            for name, memory in sorted(self.memories.items(),
                    key=lambda x: x[1].start or 0):
                memory.ls()
        if self.sections:
            print("  sections")
            for name, section in sorted(self.sections.items()):
                section.ls()
        if self.imports:
            print("  imports")
            for name, import_ in sorted(self.imports.items()):
                import_.ls()
        if self.exports:
            print("  exports")
            for name, export in sorted(self.exports.items()):
                export.ls()

class System:
    """
    Description of the top-level system which contains boxes.
    """
    __argname__ = "system"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser):
        parser.add_argument("--path",
            help="Working directory for the system, defaults to the "
                "current directory.")

        from .outputs import OUTPUTS
        outputparser = parser.add_nestedparser("--output")
        for output in OUTPUTS['sys'].values():
            outputparser.add_argument('--'+output.__argname__,
                help=output.__arghelp__)

        Memory.__argparse__(
            parser.add_set('--'+Memory.__argname__))
        Section.__argparse__(
            parser.add_set('--'+Section.__argname__))
#        sectionparser = parser.add_nestedparser("--section")
#        for section, help in Memory.SECTIONS.items():
#            Section.__argparse__(
#                sectionparser.add_nestedparser('--'+section, help=help))
        Import.__argparse__(
            parser.add_set('--'+Import.__argname__))
        Export.__argparse__(
            parser.add_set('--'+Export.__argname__))

        Box.__argparse__(
            parser.add_set('--'+Box.__argname__))

    def __init__(self, args):
        self.path = args.path or '.'

        # Load additional config from the filesystem
        try:
            parser = ArgumentParser(add_help=False)
            self.__class__.__argparse__(parser)
            nargs = parser.parse_toml(self.path + '/recipe.toml')
            args = argstuff.merge(args, nargs)
        except FileNotFoundError:
            pass

        from .outputs import OUTPUTS
        self.outputs = {name: OUTPUTS['sys'][name](self.path + '/' + path)
            for name, path in args.output.__dict__.items()
            if path}
        self.memories = {name: Memory(name, memargs)
            for name, memargs in args.memory.items()}
        self.sections = {name: Section(name, sectionargs)
            for name, sectionargs in args.section.items()}
#        self.sections = {name: Section(name, sectionargs)
#            for name, sectionargs in args.section.__dict__.items()}
        self.imports = {name: Import(name, importargs)
            for name, importargs in args.__dict__['import'].items()}
        self.exports = {name: Import(name, exportargs)
            for name, exportargs in args.export.items()}
        self.boxes = {name: Box(name, boxargs)
            for name, boxargs in args.box.items()}

#        # Figure out section placement in memories
#        # Note, this is naive and could be improved
#        # Oh, right, this is the Knapsack problem
#        romems = sorted(
#            [m for m in self.memories.values() if 'r' in m.mode],
#            key=lambda m: ('w' in m.mode)*(2<<32) +
#                ('x' in m.mode)*(1<<32) - m.size)
#        rxmems = sorted(
#            [m for m in self.memories.values() if set('rx').issubset(m.mode)],
#            key=lambda m: ('w' in m.mode)*(2<<32) - m.size)
#        rwmems = sorted(
#            [m for m in self.memories.values() if set('rw').issubset(m.mode)],
#            key=lambda m: -m.size)
#        print([m.size for m in romems])
#        print([m.size for m in rxmems])
#        print([m.size for m in rwmems])

        

        # rp  mems <- rodata
        # rxp mems <- rom, text, data
        # rw  mems <- ram, data, bss, heap, stack
        


#        for section in self.sections:
#            if section:
                

    def ls(self):
        """Show configuration on CLI."""
        print("system")
        if self.outputs:
            print("  outputs")
            for name, output in sorted(self.outputs.items()):
                print("    %-32s %s" % (name, output.path))
        if self.memories:
            print("  memories")
            for name, memory in sorted(self.memories.items(),
                    key=lambda x: x[1].start):
                memory.ls()
        if self.sections:
            print("  sections")
            for name, section in sorted(self.sections.items()):
                section.ls()
#            for name, section in sorted(self.sections.items(),
#                    key=lambda x: ({k: i for i, k in enumerate(
#                        Memory.SECTIONS.keys())})[x[0]]):
#                if section:
#                    section.ls()
        if self.imports:
            print("  imports")
            for name, import_ in sorted(self.imports.items()):
                import_.ls()
        if self.exports:
            print("  exports")
            for name, export in sorted(self.exports.items()):
                export.ls()
