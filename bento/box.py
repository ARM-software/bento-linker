
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
            help="Minimum alignment of the memory region.")
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

        mode = m.group(1) and Memory.parsemode(m.group(1))
        addr = m.group(2) and int(m.group(2), 0)
        size = m.group(3) and int(m.group(3), 0) - (
            addr - 1 if addr is not None else 0)
        if m.group(4) and int(m.group(4), 0) != size:
            raise ValueError("Range %#x-%#x does not match size %#x" % (
                addr or 0, addr+size-1, int(m.group(4), 0)))

#        if size < 0:
#            raise ValueError("Invalid range %#x?" % size)

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

    def __init__(self, name, mode=None, addr=None, size=None,
            align=None, memory=None):
        # TODO move this after assignments?
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

        assert self.size >= 0, "Invalid size %#x?" % self.size

        # modified size after memory is consumed
        self._addr = self.addr
        self._size = self.size

    def __str__(self):
        return "%(mode)s %(range)s %(size)d bytes" % dict(
            mode=''.join(c if c in self.mode else '-'
                for c in Memory.MODEFLAGS),
            range='%#010x-%#010x' % (self.addr, self.addr+self.size-1)
                if self.addr is not None else
                '%#010x' % self.size,
            size=self.size)
            # TODO need align?

    def __lt__(self, other):
        return (self.addr, self.name) < (other.addr, other.name)

    def consume(self, addr=None, size=None, align=None, reverse=False):
        if size is None:
            addr, size = None, addr or 0

        assert addr is None, "TODO" # TODO
        assert align is None, "TODO" # TODO
        assert size <= self._size

        # TODO huh
        self._addr = self._addr if self._addr is not None else self.addr
        
        if not reverse:
            self._addr += size
            self._size -= size
            return self._addr, size
        else:
            self._size -= size
            return self._addr + self._size, size

    def consumed(self):
        return self.size - self._size

    def remaining(self):
        return self._size

    def compatible(self, mode='rwx', addr=None, size=None,
            align=None, name=None):
        if size is None:
            addr, size = None, addr
        assert addr is None, "TODO" # TODO
        assert align is None, "TODO" # TODO
        return (
            self._size != 0 and
            set(mode).issubset(self.mode) and
            (size is None or size <= self._size) and
            (name is None or name == self.name))

    @staticmethod
    def compatiblekey(mode='rwx', addr=None, size=None,
            align=None, reverse=False):
        if size is None:
            addr, size = None, addr
        assert addr is None, "TODO" # TODO
        assert align is None, "TODO" # TODO
        def key(self):
            return (
                len(self.mode - set(mode)),
                -self.addr if reverse else self.addr)
        return key
#
#    def iscompatible(self, mode='rwx', size=None, consumed=0):
#        return (set(mode).issubset(self.mode) and (
#            size is None or size+consumed <= self.size) and
#            consumed != self.size)
#
#    @staticmethod
#    def bestmemories(memories, mode='rwx', size=None,
#            consumed={}, reverse=False):
#        return sorted((m for m in memories
#                if m.iscompatible(mode=mode,
#                    size=(size or 0),
#                    consumed=consumed.get(m.name, 0))),
#            key=lambda m: (
#                len(m.mode - set(mode)),
#                -m.addr if reverse else m.addr))
#
#    @staticmethod
#    def bestmemory(memories, mode='rwx', size=None,
#            consumed={}, reverse=False):
#        compatible = Memory.bestmemories(memories,
#            mode=mode, size=size,
#            consumed=consumed, reverse=reverse)
#        return compatible[0] if compatible else None

    # TODO this one is a tight fit
    def __contains__(self, other):
        if isinstance(other, Memory):
            return (other.addr >= self.addr and
                other.addr+other.size <= self.addr+self.size)
        else:
            return (other >= self.addr and
                other < self.addr + self.size)

#    def __contains__(self, other):
#        if isinstance(other, Memory):
#            return (other.addr < self.addr+self.size and
#                other.addr+other.size > self.addr)
#        else:
#            return (other >= self.addr and
#                other < self.addr + self.size)

    def __sub__(self, regions):
#        assert isinstance(other, Memory)
#        if other not in self:
#            return [self]

        if isinstance(regions, Memory):
            regions = [regions]

        if self.size == 0:
            return []

        slices = [(self.addr, self.size)]
        for region in regions:
            nslices = []
            for addr, size in slices:
                if region.addr >= addr+size or region.addr+region.size <= addr:
                    nslices.append((addr, size))
                else:
                    if region.addr > addr:
                        nslices.append((addr, region.addr - addr))
                    if addr+size > region.addr+region.size:
                        nslices.append((region.addr+region.size,
                            addr+size - region.addr+region.size))
            slices = nslices

        return [Memory(
                self.name if len(slices) == 1 else '%s%d' % (self.name, i+1),
                mode=self.mode, addr=addr, size=size, align=None)
            for i, (addr, size) in enumerate(slices)]
#
#        
#
#
#        slices = [
#            (self.addr, other.addr - self.addr),
#            (other.addr+other.size,
#                self.addr+self.size - (other.addr+other.size))]
#        slices = [(addr, size) for addr, size in slices if size > 0]
#        return [Memory(
#                self.name if len(slices) == 1 else '%s%d' % (self.name, i+1),
#                mode=self.mode, align=self.align,
#                addr=addr, size=size)
#            for i, (addr, size) in enumerate(slices)]
        

        

        

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

class Section:
    """
    Description of the SECTION. Note that the SECTION may not
    be emitted depending on specified outputs and runtimes.
    """
    __argname__ = "section"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser, name=None, help=None):
        name = name or cls.__argname__
        help = (help or cls.__arghelp__).replace('SECTION', name)
        parser.add_argument("size", type=argstuff.pred(cls.parsesection),
            metavar=name, help=help)
        parser.add_argument("--size", type=lambda x: int(x, 0),
            help="Minimum size of the %s. Defaults to 0." % name)
        parser.add_argument("--align", type=lambda x: int(x, 0),
            help="Minimum alignment of the %s." % name)

    @staticmethod
    def parsesection(s):
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

    def __init__(self, size=None, align=None):
        #assert name in Memory.SECTIONS
# TODO align and pad to alignment? (8 bytes?)
#        if args.align is not None and args.size is not None:
#            assert args.size % args.align == 0, (
#                "section size not aligned to section alignment "
#                "%#x %% %#x != 0" % (
#                    args.size, args.align))

        self.size = (Section.parsesection(size)
            if isinstance(size, str) else
            size or 0)
        self.align = align
#        if not size:
#        if 
#            self.size = None
#        try:
#            self.size = Section.parsesection(size)
#        except ValueError:
#            self.size = int(size
#        self.size = size or 0
#        self.align = align

#        self.size = size if size is not None else 4096 # TODO is 4K too small?

#        self.align = args.align or (8 if name in ['stack', 'heap'] else 4)
#        self.memory = args.memory
#

#    def __lt__(self, other):
#        # turns out this approximates the usual section order
#        # text, stack, heap, data, bss
#        return not self.name < other.name

    def __str__(self):
        return "%(size)#010x %(size)s bytes" % dict(size=self.size)

    def __bool__(self):
        return self.size != 0

#class Stack(Buffer):
#    """
#    Description of a box's stack.
#    """
#    __argname__ = "stack"
#    __arghelp__ = __doc__
#
#class Heap(Buffer):
#    """
#    Description of a box's heap.
#    """
#    __argname__ = "heap"
#    __arghelp__ = __doc__

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
        for Output in OUTPUTS['box'].values():
            outputparser.add_argument('--'+Output.__argname__,
                help=Output.__arghelp__)

#        sectionparser = parser.add_nestedparser("--section")
#        for section, help in Memory.SECTIONS.items():
#            Section.__argparse__(
#                sectionparser.add_nestedparser('--'+section, help=help))
        Memory.__argparse__(
            parser.add_set('--'+Memory.__argname__))
#        Section.__argparse__(
#            parser.add_set('--'+Section.__argname__))
#        Stack.__argparse__(
#            parser.add_nestedparser('--'+Stack.__argname__))
#        Heap.__argparse__(
#            parser.add_nestedparser('--'+Heap.__argname__))
#        Section.__argparse__(
#            parser.add_set('--'+Section.__argname__))
        Section.__argparse__(
            parser.add_nestedparser('--stack'), name='stack')
        Section.__argparse__(
            parser.add_nestedparser('--heap'), name='heap')
        Section.__argparse__(
            parser.add_nestedparser('--jumptable'), name='jumptable')
        Section.__argparse__(
            parser.add_nestedparser('--text'), name='text')
        Section.__argparse__(
            parser.add_nestedparser('--data'), name='data')
        Section.__argparse__(
            parser.add_nestedparser('--bss'), name='bss')
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
#        if self.parent:
#            for memory in reversed(self.memories):
#                if memory.addr is None:
#                    bestmemory = self.parent.bestmemory(
#                        memory.mode, reverse=True)
#                    memory.addr = (bestmemory.addr+bestmemory.size
#                        - memory.size)
#                self.parent.consumememory(memory)
        # sort again in case new addresses changed order
        #self.memories = sorted(self.memories)

        self._consumed = {memory.name: 0 for memory in self.memories}

        self.stack = Section(**args.stack.__dict__)
        self.heap = Section(**args.heap.__dict__)
        self.jumptable = Section(**args.jumptable.__dict__)
        self.text = Section(**args.text.__dict__)
        self.data = Section(**args.data.__dict__)
        self.bss = Section(**args.bss.__dict__)


#        self.sections = c.OrderedDict((x.name, x) for x in sorted(
#            Section(name, **sectionargs.__dict__)
#            for name, sectionargs in args.section.items()))


#        self.memories = {name: Memory(name, memargs)
#            for name, memargs in args.memory.items()}
#        self.sections = {name: Section(name, sectionargs)
#            for name, sectionargs in args.section.items()}
#        for section, help in Memory.SECTIONS.items():
#            Section.__argparse__(
#                parser.add_nestedparser('--'+section, help=help))
#        self.sections = {name: Section(name, sectionargs)
#            for name, sectionargs in args.section.__dict__.items()}
#        self.stack = Stack(**args.stack.__dict__)
#        self.heap = Heap(**args.heap.__dict__)
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
        self.runtime = RUNTIMES[args.runtime or 'noop']()
#        self.outputs = {name: (self.path + '/' + path, OUTPUTS['box'][name])
#            for name, path in args.output.__dict__.items()
#            if path}

        from .outputs import OUTPUTS
        self.outputs = c.OrderedDict(sorted(
            (name, OUTPUTS['box'][name](self.path + '/' + path))
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
#        for name, section in self.sections.items():
#            print('  %-34s %s' % ('section.%s' % name, section))
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

    def bestmemories_(self, mode='rwx', addr=None, size=None,
            align=None, name=None, reverse=False):
        if size is None:
            addr, size = None, addr
        return sorted((
                m for m in self.memories
                if m.compatible(mode=mode, addr=addr, size=size,
                    align=align, name=name)),
            key=Memory.compatiblekey(mode=mode, addr=addr, size=size,
                align=align, reverse=reverse))

    def bestmemory_(self, mode='rwx', addr=None, size=None,
            align=None, name=None, reverse=False):
        if size is None:
            addr, size = None, addr
        compatible = self.bestmemories_(mode=mode, addr=addr, size=size,
            align=align, name=name, reverse=reverse)
        return compatible[0] if compatible else None

    def consume(self, mode='rwx', size=None, addr=None,
            align=None, name=None, reverse=False):
        if size is None:
            addr, size = None, addr
        best = self.bestmemory_(mode=mode, addr=addr, size=size,
            align=align, name=name, reverse=reverse)
        addr, size = best.consume(addr=addr, size=size,
            align=align, reverse=reverse)
        return best, addr, size

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

    def getroot(self):
        root = self
        while root.parent:
            root = root.parent
        return root if root != self else None

    def getparent(self, n=1):
        parent = self
        for _ in range(n):
            if not self.parent:
                return None
            parent = self.parent
        return parent if parent != self else None

#    def build(self, output, builder):
#        if output in self.outputs:
#            return builder(self, self.outputs[output])
#
#    def parentbuild(self, output, builder):
#        if self.parent and output in self.parent.outputs:
#            with self.parent.outputs[output].pushattrs(
#                    parent=self.parent.name, box=self.name):
#                return builder(self.parent, self, self.parent.outputs[output])
#
#    def rootbuild(self, output, builder):
#        root = self
#        while root.parent:
#            root = root.parent
#
#        if root != self and output in root:
#            with root.outputs[output].pushattrs(
#                    root=root.name, box=self.name):
#                return builder(root, self, root.outputs[output])   

    def box(self, boxesonly=False, runtimesonly=False, outputsonly=False):
        if not runtimesonly and not outputsonly:
            if self.parent:
                for memory in self.memories:
                    _, addr, _ = self.parent.consume(
                        mode=memory.mode,
                        addr=memory.addr,
                        size=memory.size,
                        align=memory.align,
                        reverse=True)
                    if memory.addr is None:
                        memory.addr = addr

                # sort again in case new addresses changed order
                self.memories = sorted(self.memories)

            for box in self.boxes:
                box.box(boxesonly=True)

        if not boxesonly and not outputsonly:
            if self.isbox():
                self.runtime.box(self)
            else:
                from .runtimes import Runtime
                Runtime().box(self)
            for box in self.boxes:
                box.box(runtimesonly=True)

        if not boxesonly and not runtimesonly:
            for output in self.outputs.values():
                output.box(self)
            for box in self.boxes:
                box.box(outputsonly=True)

    def build(self, runtimesonly=False, outputsonly=False):
        if not outputsonly:
            for box in self.boxes:
                box.build(runtimesonly=True)
            if self.isbox():
                self.runtime.build(self)
            else:
                # TODO uh, is this the best way to do this?
                from .runtimes import Runtime
                Runtime().build(self)

        if not runtimesonly:
            for box in self.boxes:
                box.build(outputsonly=True)
            for output in self.outputs.values():
                output.build(self)

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
        for Output in OUTPUTS['sys'].values():
            outputparser.add_argument('--'+Output.__argname__,
                help=Output.__arghelp__)

        Memory.__argparse__(
            parser.add_set('--'+Memory.__argname__))
#        Section.__argparse__(
#            parser.add_set('--'+Section.__argname__))
#        sectionparser = parser.add_nestedparser("--section")
#        for section, help in Memory.SECTIONS.items():
#            Section.__argparse__(
#                sectionparser.add_nestedparser('--'+section, help=help))
#        Stack.__argparse__(
#            parser.add_nestedparser('--'+Stack.__argname__))
#        Heap.__argparse__(
#            parser.add_nestedparser('--'+Heap.__argname__))
#        Section.__argparse__(
#            parser.add_set('--'+Section.__argname__))
        Section.__argparse__(
            parser.add_nestedparser('--stack'), name='stack')
        Section.__argparse__(
            parser.add_nestedparser('--heap'), name='heap')
        Section.__argparse__(
            parser.add_nestedparser('--isr_vector'), name='isr_vector')
        Section.__argparse__(
            parser.add_nestedparser('--text'), name='text')
        Section.__argparse__(
            parser.add_nestedparser('--data'), name='data')
        Section.__argparse__(
            parser.add_nestedparser('--bss'), name='bss')
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
        self._consumed = {memory.name: 0 for memory in self.memories}
#        self.sections = {name: Section(name, sectionargs)
#            for name, sectionargs in args.section.items()}
#        self.sections = {name: Section(name, sectionargs)
#            for name, sectionargs in args.section.__dict__.items()}
#        self.stack = Stack(**args.stack.__dict__)
#        self.heap = Heap(**args.heap.__dict__)
        
#        self.sections = c.OrderedDict((x.name, x) for x in sorted(
#            Section(name, **sectionargs.__dict__)
#            for name, sectionargs in args.section.items()))
        self.stack = Section(**args.stack.__dict__)
        self.heap = Section(**args.heap.__dict__)
        self.isr_vector = Section(**{**args.isr_vector.__dict__,
            'size': args.isr_vector.size
                if args.isr_vector.size is not None else
                0x400})
        self.text = Section(**args.text.__dict__)
        self.data = Section(**args.data.__dict__)
        self.bss = Section(**args.bss.__dict__)

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
            (name, OUTPUTS['box'][name](path))
            for name, path in args.output.__dict__.items()
            if path))
                

    def ls(self):
        """Show configuration on CLI."""
        print('system')
        for memory in self.memories:
            print('  %-34s %s' % ('memory.%s' % memory.name, memory))
#        for name, section in self.sections.items():
#            print('  %-34s %s' % ('section.%s' % name, section))
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
