
import re
import collections as c
import itertools as it
from . import argstuff
from .argstuff import ArgumentParser
#
#
#class Output:
#    """
#    Description of an output file of type OUTPUT.
#    """
#    def __init__(self, name, path=None, cls=None):
#
#
#
#        from .outputs import OUTPUTS
#        outputparser = parser.add_nestedparser("--output")
#        for output in OUTPUTS['box'].values():
#            outputparser.add_argument('--'+output.__argname__,
#                help=output.__arghelp__)
#        from .outputs import OUTPUTS
#        self.outputs = {name: (self.path + '/' + path, OUTPUTS['sys'][name])
#            for name, path in args.output.__dict__.items()
#            if path}

class Memory:
    """
    Description of a memory region named MEMORY.
    """
    MODEFLAGS = ['r', 'w', 'x']

    __argname__ = "memory"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser):
        parser.add_argument("memory", type=argstuff.pred(cls.parsememory),
            help=cls.__arghelp__)
        parser.add_argument("--mode", type=argstuff.pred(cls.parsemode),
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
        if any(c not in Memory.MODEFLAGS for c in s):
            raise ValueError("invalid memory mode %r" % s)
        return set(s)

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

    def __init__(self, name, memory=None, mode=None, align=None,
            addr=None, size=None):
        if align is not None:
            if addr is not None:
                assert addr % align == 0, (
                    "memory region not aligned to section alignment "
                    "%#x %% %#x != 0" % (
                        addr, align))
            if size is not None:
                assert size % align == 0, (
                    "memory region not aligned to section alignment "
                    "%#x %% %#x != 0" % (
                        size, align))

        self.name = name
        memory = Memory.parsememory(memory) if memory else (None, None, None)
        self.mode = Memory.parsemode(mode) if mode else memory[0] or set()
        self.align = align
        self.addr = addr if addr is not None else memory[1]
        self.size = size if size is not None else memory[2] or 0
        #self.sections = args.sections # TODO rm me?

    def __str__(self):
        return "%(mode)s %(range)s %(size)d bytes%(align)s" % dict(
            mode=''.join(c if c in self.mode else '-'
                for c in Memory.MODEFLAGS),
            range='%#010x-%#010x' % (self.addr, self.addr+self.size-1)
                if self.addr is not None else
                '%#010x' % self.size,
            size=self.size,
            align=' %s align' % self.align if self.align is not None else '')
            # TODO need align?

    def __lt__(self, other):
        return (self.addr, self.name) < (other.addr, other.name)

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

    def __contains__(self, other):
        if isinstance(other, Memory):
            return (other.addr < self.addr+self.size and
                other.addr+other.size > self.addr)
        else:
            return (other >= self.addr and
                other < self.addr + self.size)

    def __sub__(self, other):
        assert isinstance(other, Memory)
        if other not in self:
            return [self]

        slices = [
            (self.addr, other.addr - self.addr),
            (other.addr+other.size,
                self.addr+self.size - (other.addr+other.size))]
        slices = [(addr, size) for addr, size in slices if size > 0]
        return [Memory(
                self.name if len(slices) == 1 else '%s%d' % (self.name, i+1),
                mode=self.mode, align=self.align,
                addr=addr, size=size)
            for i, (addr, size) in enumerate(slices)]
        

        

        

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
        parser.add_argument("size", type=argstuff.pred(cls.parsebuffer),
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

    def __init__(self, size):
        #assert name in Memory.SECTIONS
# TODO align and pad to alignment? (8 bytes?)
#        if args.align is not None and args.size is not None:
#            assert args.size % args.align == 0, (
#                "section size not aligned to section alignment "
#                "%#x %% %#x != 0" % (
#                    args.size, args.align))

        self.size = size if size is not None else 4096 # TODO is 4K too small?

#        self.align = args.align or (8 if name in ['stack', 'heap'] else 4)
#        self.memory = args.memory
#

    def __str__(self):
        return "%(size)#010x %(size)s bytes" % dict(size=self.size)

    def __bool__(self):
        return self.size != 0

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
        parser.add_argument("type", type=argstuff.pred(cls.parsetype),
            help=cls.__arghelp__)
        parser.add_argument("--type", type=argstuff.pred(cls.parsetype),
            help="Type of the function.")
        parser.add_argument("--doc",
            help="Docstring for the function.")
#    @classmethod
#    def __arginit__(cls, name, args):
#        argtypes, argnames, rettypes, retnames = args.__dict__.pop('type')
#        return cls(name, **{**dict(
#            argtypes=argtypes, argnames=argnames,
#            rettypes=rettypes, retnames=retnames),
#            **args.__dict__})

    @staticmethod
    def parsetype(s):
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

    def __init__(self, name, type, doc=None):
        self.name = name
        self.doc = doc

        argtypes, argnames, rettypes, retnames = Fn.parsetype(type)
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

    def __init__(self, name, parent=None, **args):
        args = argstuff.Namespace(**args)
        self.name = name
        self.parent = parent
        self.path = args.path or name

        # Load additional config from the filesystem
        try:
            parser = ArgumentParser(add_help=False)
            self.__class__.__argparse__(parser)
            nargs = parser.parse_toml(self.path + '/recipe.toml')
            args = argstuff.merge(args, nargs)
        except FileNotFoundError:
            pass

        self.memories = sorted(Memory(name, **memargs.__dict__)
            for name, memargs in args.memory.items())
        #self.original_memories = self.memories
        if self.parent:
            for memory in reversed(self.memories):
                if memory.addr is None:
                    bestmemory = self.parent.bestmemory(
                        memory.mode, reverse=True)
                    memory.addr = (bestmemory.addr+bestmemory.size
                        - memory.size)
                self.parent.consumememory(memory)
        # sort again in case new addresses changed order
        self.memories = sorted(self.memories)




#        self.memories = {name: Memory(name, memargs)
#            for name, memargs in args.memory.items()}
#        self.sections = {name: Section(name, sectionargs)
#            for name, sectionargs in args.section.items()}
#        for section, help in Memory.SECTIONS.items():
#            Section.__argparse__(
#                parser.add_nestedparser('--'+section, help=help))
#        self.sections = {name: Section(name, sectionargs)
#            for name, sectionargs in args.section.__dict__.items()}
        self.stack = Stack(**args.stack.__dict__)
        self.heap = Heap(**args.heap.__dict__)
#        self.imports = {name: Import(name, importargs)
#            for name, importargs in args.__dict__['import'].items()}
#        self.exports = {name: Import(name, exportargs)
#            for name, exportargs in args.export.items()}
#        self.imports = sorted(Import(name, importargs)
#            for name, importargs in args.__dict__['import'].items())
#        self.exports = sorted(Import(name, exportargs)
#            for name, exportargs in args.export.items())
        self.imports = sorted(Import(name, **importargs.__dict__)
            for name, importargs in args.__dict__['import'].items())
        self.exports = sorted(Import(name, **exportargs.__dict__)
            for name, exportargs in args.export.items())

        # TODO hmm ( ͡° ͜ʖ ͡°)
        self.boxes = []

        from .runtimes import RUNTIMES
        self.runtime = RUNTIMES[args.runtime or 'noop'](self)
#        self.outputs = {name: (self.path + '/' + path, OUTPUTS['box'][name])
#            for name, path in args.output.__dict__.items()
#            if path}

        from .outputs import OUTPUTS
        self.outputs = c.OrderedDict(sorted(
            (name, OUTPUTS['box'][name](self, path))
            for name, path in args.output.__dict__.items()
            if path))

    def ls(self):
        """Show configuration on CLI."""
        # TODO move this to __main__.py actually?
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

    def __eq__(self, other):
        return (self.isbox(), self.name) == (other.isbox(), other.name)

    def __lt__(self, other):
        return (self.isbox(), self.name) < (other.isbox(), other.name)

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

    def consumememory(self, region):
        nmemories = []
        for memory in self.memories:
            if region in memory:
                slices = memory - region
                nmemories.extend(slices)
            else:
                nmemories.append(memory)
        self.memories = sorted(nmemories)

    def issys(self):
        return False

    def isbox(self):
        return not self.issys()

    def build(self, output, builder):
        if output in self.outputs:
            return builder(self, self.outputs[output])

    def parentbuild(self, output, builder):
        if self.parent and output in self.parent.outputs:
            with self.parent.outputs[output].pushattrs(
                    parent=self.parent.name, box=self.name):
                return builder(self.parent, self, self.parent.outputs[output])

    def rootbuild(self, output, builder):
        root = self
        while root.parent:
            root = root.parent

        if root != self and output in root:
            with root.outputs[output].pushattrs(
                    root=root.name, box=self.name):
                return builder(root, self, root.outputs[output])

class System(Box):
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

    def __init__(self, **args):
        args = argstuff.Namespace(**args)
        self.name = None
        self.parent = None
        self.path = args.path or '.'

        # Load additional config from the filesystem
        try:
            parser = ArgumentParser(add_help=False)
            self.__class__.__argparse__(parser)
            nargs = parser.parse_toml(self.path + '/recipe.toml')
            args = argstuff.merge(args, nargs)
        except FileNotFoundError:
            pass

#        self.memories = {name: Memory(name, memargs)
#            for name, memargs in args.memory.items()}
        self.memories = sorted(Memory(name, **memargs.__dict__)
            for name, memargs in args.memory.items())
#        self.sections = {name: Section(name, sectionargs)
#            for name, sectionargs in args.section.items()}
#        self.sections = {name: Section(name, sectionargs)
#            for name, sectionargs in args.section.__dict__.items()}
        self.stack = Stack(**args.stack.__dict__)
        self.heap = Heap(**args.heap.__dict__)
        self.imports = sorted(Import(name, **importargs.__dict__)
            for name, importargs in args.__dict__['import'].items())
        self.exports = sorted(Import(name, **exportargs.__dict__)
            for name, exportargs in args.export.items())
#        self.imports = sorted(Import(name, importargs)
#            for name, importargs in args.__dict__['import'].items())
#        self.exports = sorted(Import(name, exportargs)
#            for name, exportargs in args.export.items())
#        self.imports = {name: Import(name, importargs)
#            for name, importargs in args.__dict__['import'].items()}
#        self.exports = {name: Import(name, exportargs)
#            for name, exportargs in args.export.items()}
#        self.boxes = {name: Box(name, boxargs)
#            for name, boxargs in args.box.items()}

        

        self.boxes = sorted(Box(name, **boxargs.__dict__, parent=self)
            for name, boxargs in sorted(args.box.items(), reverse=True))

#        # TODO assign box memory in reverse order
#        for box in reversed(self.boxes):
#            for memory in reversed(box.memories):
#                if memory.addr is None:
#                    # TODO hm, mutable??
#                    bestmemory = box.bestmemory(memory.mode, reverse=True)
#                    memory.addr = bestmemory.addr - memory.size
#
#                self.consumememory(memory)
                    

        # TODO omit our overlapping regions

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


        from .outputs import OUTPUTS
#        self.outputs = {name: (self.path + '/' + path, OUTPUTS['sys'][name])
#            for name, path in args.output.__dict__.items()
#            if path}
        self.outputs = c.OrderedDict(sorted(
            (name, OUTPUTS['box'][name](self, path))
            for name, path in args.output.__dict__.items()
            if path))
                

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

#    def bestmemories(self, mode='rwx', size=None,
#            consumed={}, reverse=False):
#        # TODO inline?
#        return Memory.bestmemories(self.memories,
#            mode=mode, size=size, consumed=consumed, reverse=reverse)
#
#    def bestmemory(self, mode='rwx', size=None,
#            consumed={}, reverse=False):
#        # TODO inline?
#        return Memory.bestmemory(self.memories,
#            mode=mode, size=size, consumed=consumed, reverse=reverse)

    def issys(self):
        return True
