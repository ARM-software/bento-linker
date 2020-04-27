
import re
import collections as c
import itertools as it
from . import argstuff
from .argstuff import ArgumentParser

class Memory:
    """
    Description of a memory region named MEMORY.
    """
    MODEFLAGS = ['r', 'w', 'x']

    __argname__ = "memory"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser):
        parser.add_argument("memory", type=cls.parsememory,
            help=cls.__arghelp__)
        parser.add_argument("--mode", type=cls.parsemode,
            help="String of characters indicating how the underlying memory "
                "can be accessed. Can be a combination of %s." %
                ', '.join(map(repr, cls.MODEFLAGS)))
        parser.add_argument("--addr", type=lambda x: int(x, 0),
            help="Starting address of memory region. Note that addr may be "
                "undefined if the exact location does not matter.")
        parser.add_argument("--size", type=lambda x: int(x, 0),
            help="Size of memory region in bytes.")
        parser.add_argument("--align", type=lambda x: int(x, 0),
            help="Minimum alignment of the memory region. Used for sanity "
                "check but otherwise unused unless addr is not specified.")
#        parser.add_argument("--sections", type=cls.parsesections,
#            help="List of sections to place in this memory region. If not "
#                "specified, %%(prog)s will try to place sections in the "
#                "largest compatible memory region.")

    @staticmethod
    def parsemode(s):
        flags = set()
        for c in s:
            if c not in Memory.MODEFLAGS:
                raise ValueError("invalid memory mode %r" % s)
            flags.add(c)
        return flags

    @staticmethod
    def parsememory(s):
        addrpattern = r'(?:0[a-z])?[0-9a-fA-F]+'
        mempattern = (r'\s*'
            '([a-z-]+(?=\s|$))?\s*'
            '(?:(%(addr)s)\s*-)?\s*'
            '(%(addr)s)?\s*'
            '(%(addr)s)?\s*'
            '(?:bytes)?\s*' % dict(addr=addrpattern))

        m = re.match('^%s$' % mempattern, s)
        if not m:
            raise ValueError("Invalid memory description %r" % s)

        mode = Memory.parsemode(m.group(1)) if m.group(1) else None
        addr = int(m.group(2), 0) if m.group(2) else None
        size = int(m.group(3), 0) - (addr or 0) + 1 if m.group(3) else None
        if m.group(4) and int(m.group(4), 0) != size:
            raise ValueError("Range %#x-%#x does not match size %#x" % (
                addr or 0, addr+size-1, int(m.group(4), 0)))

        return mode, addr, size

##    SECTIONS = c.OrderedDict([
##        ('rom', "Meta-section containing all readonly sections. This is the "
##            "combination of the read-only sections and the init copy of the "
##            "data section."),
##        ('ram', "Meta-section containing all read/write sections. This is the "
##            "combination of the bss, data, stack, and heap sections."),
##        ('text', "Text section "
##            "containing executable code."),
##        ('rodata', "RO Data section "
##            "containing read-only data."),
##        ('bss', "BSS section "
##            "containing read/write data that is zero-initialized."),
##        ('data', "Data section "
##            "containing read/write data with initialization."),
##        ('stack', "Stack section "
##            "containing the stack for execution."),
##        ('heap', "Heap section "
##            "containing the heap for execution.")])
#    @staticmethod
#    def parsesections(s):
#        sections = s.split()
##        for section in sections:
##            if section not in Memory.SECTIONS:
##                raise ValueError("invalid section %r" % section)
#        return sections

    def __init__(self, name, args):
        if args.align is not None:
            if args.addr is not None:
                assert args.addr % args.align == 0, (
                    "memory region not aligned to section alignment "
                    "%#x %% %#x != 0" % (
                        args.addr, args.align))
            if args.size is not None:
                assert args.size % args.align == 0, (
                    "memory region not aligned to section alignment "
                    "%#x %% %#x != 0" % (
                        args.size, args.align))

        self.name = name
        memory = args.memory or (None, None, None)
        self.mode = args.mode or memory[0] or ''
        self.addr = args.addr or memory[1]
        self.size = args.size or memory[2] or 0
        self.align = args.align
        #self.sections = args.sections # TODO rm me?

    def __str__(self):
        return "%(mode)s %(range)s %(size)d bytes%(align)s" % dict(
            mode=''.join(c if c in self.mode else '-'
                for c in Memory.MODEFLAGS),
            range='%#010x-%#010x' % (self.addr, self.addr+self.size-1)
                if self.addr else
                '%#010x' % self.size,
            size=self.size,
            align=' %s align' % self.align if self.align is not None else '')
            # TODO need align?

    def __lt__(self, other):
        return self.addr < other.addr

    def iscompatible(self, mode='rwx', size=None):
        return set(mode).issubset(self.mode) and (
            size is None or size <= self.size)

    @staticmethod
    def bestmemories(memories, mode='rwx', size=None,
            consumed={}, reverse=False):
        return sorted((m for m in memories
                if m.iscompatible(mode=mode,
                    size=(size or 0)+consumed.get(m.name, 0))),
            key=lambda m: (
                len(m.mode - set(mode)),
                -m.addr if reverse else m.addr))

    @staticmethod
    def bestmemory(memories, mode='rwx', size=None,
            consumed={}, reverse=False):
        compatible = Memory.bestmemories(memories,
            mode=mode, size=size,
            consumed=consumed, reverse=reverse)
        return compatible[0] if compatible else None
        

#    def ls(self):
#        """Show configuration on CLI."""
#        print("    %-32s %s%s %d bytes%s" % (
#            self.name,
#            ''.join(c if c in self.mode else '-'
#                for c in Memory.MODEFLAGS),
#            ' %#010x-%#010x' % (self.start, self.start+self.size-1)
#                if self.start else
#            ' %#010x' % self.size,
#            self.size,
#            ' %s align' % self.align if self.align is not None else ''))

class Buffer:
    """
    Description of a dynamic buffer.
    """
    @classmethod
    def __argparse__(cls, parser):
        parser.add_argument("size", type=cls.parsebuffer,
            metavar=cls.__argname__.upper(), help=cls.__arghelp__)
        parser.add_argument("--size", type=lambda x: int(x, 0),
            help="Minimum size of the %s. Note, may go unused depending on "
                "specified outputs. Defaults to 4096." % cls.__argname__)

    @staticmethod
    def parsebuffer(s):
        addrpattern = r'(?:0[a-z])?[0-9a-fA-F]+'
        bufferpattern = (r'\s*'
            '(%(addr)s)?\s*'
            '(%(addr)s)?\s*'
            '(?:bytes)?\s*' % dict(addr=addrpattern))

        m = re.match('^%s$' % bufferpattern, s)
        if not m:
            raise ValueError("Invalid %s description %r" % (
                cls.__argname__, s))

        size = int(m.group(1), 0) if m.group(1) else None
        if m.group(2) and int(m.group(2), 0) != size:
            raise ValueError("Range %#x does not match size %#x" % (
                size, int(m.group(4), 0)))

        return size

    def __init__(self, args):
        #assert name in Memory.SECTIONS
# TODO align and pad to alignment? (8 bytes?)
#        if args.align is not None and args.size is not None:
#            assert args.size % args.align == 0, (
#                "section size not aligned to section alignment "
#                "%#x %% %#x != 0" % (
#                    args.size, args.align))

        self.size = args.size or 4096 # TODO is 4K too small?

#        self.align = args.align or (8 if name in ['stack', 'heap'] else 4)
#        self.memory = args.memory
#

    def __str__(self):
        return "%(size)#010x %(size)s bytes" % dict(size=self.size)

    def __bool__(self):
        return bool(self.size)

class Stack(Buffer):
    """
    Description of a box's stack.
    """
    __argname__ = "stack"
    __arghelp__ = __doc__

class Heap(Buffer):
    """
    Description of a box's heap.
    """
    __argname__ = "heap"
    __arghelp__ = __doc__

#class Section:
#    """
#    Description of a linking section named SECTION.
#    """
#    __argname__ = "section"
#    __arghelp__ = __doc__
#    @classmethod
#    def __argparse__(cls, parser):
#        parser.add_argument("--size", type=lambda x: int(x, 0),
#            help="Minimum size of the section.")
#        parser.add_argument("--align", type=lambda x: int(x, 0),
#            help="Minimum alignment of the section. Defaults to 8 bytes for "
#                "stack/heap, 4 bytes otherwise")
##        parser.add_argument("--memory",
##            help="Explicitly state which memory region to place section in. "
##                "If not specified, the sections specified in each memory "
##                "region will be used.")
#
#    def __init__(self, name, args):
#        #assert name in Memory.SECTIONS
#        if args.align is not None and args.size is not None:
#            assert args.size % args.align == 0, (
#                "section size not aligned to section alignment "
#                "%#x %% %#x != 0" % (
#                    args.size, args.align))
#
#        self.name = name
#        self.size = args.size or 0
#        self.align = args.align
#        self.memory = None
##        self.align = args.align or (8 if name in ['stack', 'heap'] else 4)
##        self.memory = args.memory
##
##    def __bool__(self):
##        return self.size is not None
#
#    def ls(self):
#        """Show configuration on CLI."""
#        # TODO print memory here?
#        print("    %-32s %#010x %s bytes%s%s" % (
#            self.name,
#            self.size,
#            self.size,
#            ' %s align' % self.align if self.align is not None else '',
#            ' in %s' % self.memory.name if self.memory is not None else ''))

class Type:
    """
    Type of function argument or return value.
    """
    PRIMITIVE_TYPES = [
        'u8', 'u16', 'u32', 'u64', 'usize',
        'i8', 'i16', 'i32', 'i64', 'isize',
        'f32', 'f64']
    PRIMITIVE_ALIASES = [
        (r'\buint(\d+)_t\b',    r'u\1'),
        (r'\bint(\d+)_t\b',     r'i\1'),
        (r'\bsize_t\b',         r'usize'),
        (r'\bssize_t\b',        r'isize'),
        (r'\bfloat\b',          r'f32'),
        (r'\bdouble\b',         r'f64'),
        (r'\bvoid *\*\b',       r'u8*')]
    def __init__(self, type):
        for pattern, repl in it.chain([(r' +', r'')], Type.PRIMITIVE_ALIASES):
            type = re.sub(pattern, repl, type)

        m = re.match(r'^(%s)(\**)$' % '|'.join(Type.PRIMITIVE_TYPES), type)
        if not m:
            raise ValueError("Invalid type %r" % type)

        self._primitive = m.group(1)
        self._ptr = m.group(2)

        if len(self._ptr) > 1:
            raise ValueError(
                "Indirect pointers currently not supported in type %r" % type)

    def isptr():
        return bool(self._ptr)

    def __str__(self, argname=None):
        if argname:
            return '%s %s%s' % (self._primitive, self._ptr, argname)
        else:
            return '%s%s' % (self._primitive, self._ptr)

    def repr_c(self, name=None):
        if self._primitive == 'u8' and self._ptr:
            primitive = 'void'
        elif self._primitive == 'usize':
            primitive = 'size_t'
        elif self._primitive == 'isize':
            primitive = 'ssize_t'
        elif self._primitive.startswith('u'):
            primitive = 'uint%s_t' % self._primitive[1:]
        elif self._primitive.startswith('i'):
            primitive = 'int%s_t' % self._primitive[1:]
        elif self._primitive == 'f32':
            primtive = 'float'
        elif self._primitive == 'f64':
            primtive = 'double'
        else:
            assert False

        if name:
            return '%s %s%s' % (primitive, self._ptr, name)
        else:
            return '%s%s' % (primitive, self._ptr)

class Fn:
    """
    Function type.
    """
    @classmethod
    def __argparse__(cls, parser):
        parser.add_argument("type", type=cls.parse,
            help=cls.__arghelp__)
        parser.add_argument("--type", type=cls.parse,
            help="Type of the function.")
        parser.add_argument("--doc",
            help="Docstring for the function.")

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
        argnames = []
        for arg in rawargs:
            if arg:
                m = re.match('^%s$' % argpattern, arg.strip())
                name = m.group(2) or m.group(5)
                type = (m.group(1) or m.group(3) or m.group(4)).replace(' ', '')
                args.append(type)
                argnames.append(name)
        if args == ['void']:
            args = []

        rets = []
        retnames = []
        for ret in rawrets:
            if ret:
                m = re.match('^%s$' % argpattern, ret.strip())
                name = m.group(2) or m.group(5)
                type = (m.group(1) or m.group(3) or m.group(4)).replace(' ', '')
                rets.append(type)
                retnames.append(name)
        if rets == ['void']:
            rets = []

        if len(rets) > 1:
            # TODO show this message in argparse error?
            raise ValueError("Currently on 0 or 1 return value supported")

        return args, argnames, rets, retnames
#        return (
#            # TODO move to init?
#            [Type(a) for a in args], argnames,
#            [Type(r) for r in rets], retnames)
#        try:
#            return ([Type(a) for a in args], [Type(r) for r in rets])
#        except Exception as e:
#            print(e)
#            raise

    def __init__(self, name, args):
        self.name = name
        self.doc = args.doc
        argtypes, argnames, rettypes, retnames = args.type or args.type

        self.args = [Type(arg) for arg in argtypes]
        self.argnames = [name or 'a%d' % i for i, name in enumerate(argnames)]
        self.rets = [Type(ret) for ret in rettypes]
        self.retnames = [name or 'a%d' % i for i, name in enumerate(retnames)]

    def __str__(self):
        return 'fn(%s) -> %s' % (
            ', '.join(map(str, self.args)),
            'void' if not self.rets else
            ', '.join(map(str, self.rets)))

    def __lt__(self, other):
        return self.name < other.name

#    def ls(self):
#        """Show configuration on CLI."""
#        print("    %-32s %s" % (self.name, self))

    def repr_c(self, name=None):
        return "%(rets)s %(name)s(%(args)s)" % dict(
            name=name or self.name,
            args='void' if len(self.args) == 0 else
                ', '.join(arg.repr_c(name) for arg, name in
                    zip(self.args, self.argnames)),
            rets='void' if len(self.rets) == 0 else 
                ', '.join(ret.repr_c() for ret in self.rets))
        
    def repr_c_ptr(self):
        return self.repr_c(name='(*%s)' % self.name)

class Import(Fn):
    """
    Description of an imported function for a box.
    """
    __argname__ = "import"
    __arghelp__ = __doc__
#
#    @staticmethod
#    def parse(s):
#        namepattern = r'[a-zA-Z_][a-zA-Z_0-9]*'
#        typepattern = r'%(name)s(?:\s*[\*\&])*' % dict(name=namepattern)
#        # three arg permutations: tpye, name: type, type name
#        argpattern = (r'(?:'
#                r'(%(type)s)|'
#                r'(%(name)s):\s*(%(type)s)|'
#                r'(%(type)s)\s*(%(name)s)'
#            r')' % dict(name=namepattern, type=typepattern))
#        # functions with and without parens around args/rets
#        fnpattern = (r'\s*fn\s*(?:'
#                r'\(\s*((?:%(arg)s(?:\s*,\s*%(arg)s)*)?)\s*\)|'
#                r'((?:%(arg)s(?:\s*,\s*%(arg)s)*)?)'
#            r')\s*->\s*(?:'
#                r'\(\s*((?:%(arg)s(?:\s*,\s*%(arg)s)*)?)\s*\)|'
#                r'((?:%(arg)s(?:\s*,\s*%(arg)s)*)?)'
#            r')\s*' % dict(arg=argpattern))
#
#        m = re.match('^%s$' % fnpattern, s)
#        if not m:
#            raise ValueError("Invalid import/export type %r" % s)
#
#        rawargs = (m.group(1) or m.group(12) or '').split(',')
#        rawrets = (m.group(23) or m.group(34) or '').split(',') # 35?
#
#        args = []
#        for arg in rawargs:
#            if arg:
#                m = re.match('^%s$' % argpattern, arg.strip())
#                name = m.group(2) or m.group(5)
#                type = (m.group(1) or m.group(3) or m.group(4)).replace(' ', '')
#                args.append(type)
#        if args == ['void']:
#            args = []
#
#        rets = []
#        for ret in rawrets:
#            if ret:
#                m = re.match('^%s$' % argpattern, ret.strip())
#                name = m.group(2) or m.group(5)
#                type = (m.group(1) or m.group(3) or m.group(4)).replace(' ', '')
#                rets.append(type)
#        if rets == ['void']:
#            rets = []
#
#        return ([Type(a) for a in args], [Type(r) for r in rets])
##        try:
##            return ([Type(a) for a in args], [Type(r) for r in rets])
##        except Exception as e:
##            print(e)
##            raise
#
#    def __init__(self, name, args):
#        self.name = name
#        self.args, self.rets = args.type
#
#    def ls(self):
#        """Show configuration on CLI."""
#        print("    %-32s fn(%s) -> %s" % (
#            self.name, ', '.join(self.args), ', '.join(self.rets)))

class Export(Fn):
    """
    Description of an exported function for a box.
    """
    __argname__ = "export"
    __arghelp__ = __doc__

class Box:
    """
    Description of a given box named BOX.
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
#        Section.__argparse__(
#            parser.add_set('--'+Section.__argname__))
        Stack.__argparse__(
            parser.add_nestedparser('--'+Stack.__argname__))
        Heap.__argparse__(
            parser.add_nestedparser('--'+Heap.__argname__))
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
        self.outputs = {name: (self.path + '/' + path, OUTPUTS['box'][name])
            for name, path in args.output.__dict__.items()
            if path}
        self.memories = sorted(Memory(name, memargs)
            for name, memargs in args.memory.items())
#        self.memories = {name: Memory(name, memargs)
#            for name, memargs in args.memory.items()}
#        self.sections = {name: Section(name, sectionargs)
#            for name, sectionargs in args.section.items()}
#        for section, help in Memory.SECTIONS.items():
#            Section.__argparse__(
#                parser.add_nestedparser('--'+section, help=help))
#        self.sections = {name: Section(name, sectionargs)
#            for name, sectionargs in args.section.__dict__.items()}
        self.stack = Stack(args.stack)
        self.heap = Heap(args.heap)
#        self.imports = {name: Import(name, importargs)
#            for name, importargs in args.__dict__['import'].items()}
#        self.exports = {name: Import(name, exportargs)
#            for name, exportargs in args.export.items()}
        self.imports = sorted(Import(name, importargs)
            for name, importargs in args.__dict__['import'].items())
        self.exports = sorted(Import(name, exportargs)
            for name, exportargs in args.export.items())

    def __lt__(self, other):
        return self.name < other.name

    def ls(self):
        """Show configuration on CLI."""
        print("box %s" % self.name)
        print("  %(name)-34s %(runtime)s" % dict(
            name="runtime",
            runtime=self.runtime.__argname__))
        for memory in self.memories:
            print('  %-34s %s' % ('memory.%s' % memory.name, memory))
        print('  %-34s %s' % ('stack', self.stack))
        print('  %-34s %s' % ('heap', self.heap))
        if self.imports:
            print('  import')
            for import_ in self.imports:
                print('    %-32s %s' % (import_.name, import_))
        if self.exports:
            print('  export')
            for export in self.exports:
                print('    %-32s %s' % (export.name, export))

    def bestmemories(self, mode='rwx', size=None,
            consumed={}, reverse=False):
        # TODO inline?
        return Memory.bestmemories(self.memories,
            mode=mode, size=size, consumed=consumed, reverse=reverse)

    def bestmemory(self, mode='rwx', size=None,
            consumed={}, reverse=False):
        # TODO inline?
        return Memory.bestmemory(self.memories,
            mode=mode, size=size, consumed=consumed, reverse=reverse)

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
#        Section.__argparse__(
#            parser.add_set('--'+Section.__argname__))
#        sectionparser = parser.add_nestedparser("--section")
#        for section, help in Memory.SECTIONS.items():
#            Section.__argparse__(
#                sectionparser.add_nestedparser('--'+section, help=help))
        Stack.__argparse__(
            parser.add_nestedparser('--'+Stack.__argname__))
        Heap.__argparse__(
            parser.add_nestedparser('--'+Heap.__argname__))
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
        self.outputs = {name: (self.path + '/' + path, OUTPUTS['sys'][name])
            for name, path in args.output.__dict__.items()
            if path}
#        self.memories = {name: Memory(name, memargs)
#            for name, memargs in args.memory.items()}
        self.memories = sorted(Memory(name, memargs)
            for name, memargs in args.memory.items())
#        self.sections = {name: Section(name, sectionargs)
#            for name, sectionargs in args.section.items()}
#        self.sections = {name: Section(name, sectionargs)
#            for name, sectionargs in args.section.__dict__.items()}
        self.stack = Stack(args.stack)
        self.heap = Heap(args.stack)
        self.imports = sorted(Import(name, importargs)
            for name, importargs in args.__dict__['import'].items())
        self.exports = sorted(Import(name, exportargs)
            for name, exportargs in args.export.items())
#        self.imports = {name: Import(name, importargs)
#            for name, importargs in args.__dict__['import'].items()}
#        self.exports = {name: Import(name, exportargs)
#            for name, exportargs in args.export.items()}
#        self.boxes = {name: Box(name, boxargs)
#            for name, boxargs in args.box.items()}
        self.boxes = sorted(Box(name, boxargs)
            for name, boxargs in args.box.items())

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
        print('system')
        for memory in self.memories:
            print('  %-34s %s' % ('memory.%s' % memory.name, memory))
        print('  %-34s %s' % ('stack', self.stack))
        print('  %-34s %s' % ('heap', self.heap))
        if self.imports:
            print('  import')
            for import_ in self.imports:
                print('    %-32s %s' % (import_.name, import_))
        if self.exports:
            print('  export')
            for export in self.exports:
                print('    %-32s %s' % (export.name, export))

    def bestmemories(self, mode='rwx', size=None,
            consumed={}, reverse=False):
        # TODO inline?
        return Memory.bestmemories(self.memories,
            mode=mode, size=size, consumed=consumed, reverse=reverse)

    def bestmemory(self, mode='rwx', size=None,
            consumed={}, reverse=False):
        # TODO inline?
        return Memory.bestmemory(self.memories,
            mode=mode, size=size, consumed=consumed, reverse=reverse)
