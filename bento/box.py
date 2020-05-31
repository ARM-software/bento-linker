
import re
import collections as co
import itertools as it
import os
from . import argstuff
from .argstuff import ArgumentParser


class Section:
    """
    Description of the SECTION section. Note that the SECTION section
    may not be emitted depending on specified outputs and runtimes.
    """
    __argname__ = "section"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser, name=None, help=None):
        name = name or cls.__argname__
        help = (help or cls.__arghelp__).replace('SECTION', name)
        parser.add_argument("size", pred=cls.parsesection,
            metavar=name, help=help)
        parser.add_argument("--size", type=lambda x: int(x, 0),
            help="Minimum size of the %s. Defaults to 0." % name)
        parser.add_argument("--align", type=lambda x: int(x, 0),
            help="Minimum alignment of the %s. Optional." % name)
        parser.add_argument("--memory",
            help="Explicitly specify the memory to allocate the %s." % name)

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

    def __init__(self, size=None, align=None, memory=None):
        self.size = (Section.parsesection(size)
            if isinstance(size, str) else
            size or 0)
        self.align = align
        self.memory = memory

        if self.align:
            assert self.size % self.align == 0, ("Section size %#010x "
                "not aligned to section alignment %#010x" % (
                    self.size, self.align))

    def __str__(self):
        return "%(size)#010x %(size)s bytes" % dict(size=self.size)

    def __bool__(self):
        return self.size != 0

class Region:
    """
    Region of addresses to use for REGION.
    """
    __argname__ = "region"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser, name=None, help=None):
        name = name or cls.__argname__
        help = (help or cls.__arghelp__).replace('REGION', name)
        parser.add_argument("region", pred=cls.parseregion,
            help=cls.__arghelp__)
        parser.add_argument("--addr", type=lambda x: int(x, 0),
            help="Starting address of region. Note that addr may be "
                "undefined if the exact location does not matter.")
        parser.add_argument("--size", type=lambda x: int(x, 0),
            help="Size of the region in bytes.")
        parser.add_argument("--align", type=lambda x: int(x, 0),
            help="Minimum alignment of the region. Optional.")

    @staticmethod
    def parseregion(s):
        addrpattern = r'(?:0[a-z])?[0-9a-fA-F]+'
        mempattern = (r'\s*'
            '(?:(%(addr)s)\s*-)?\s*'
            '(%(addr)s)?\s*'
            '(%(addr)s)?\s*'
            '(?:bytes)?\s*' % dict(addr=addrpattern))

        m = re.match('^%s$' % mempattern, s)
        if not m:
            raise ValueError("Invalid region description %r" % s)

        addr = m.group(1) and int(m.group(1), 0)
        size = m.group(2) and int(m.group(2), 0) - (
            addr - 1 if addr is not None else 0)
        if m.group(3) and int(m.group(3), 0) != size:
            raise ValueError("Range %#x-%#x does not match size %#x" % (
                addr or 0, addr+size-1, int(m.group(3), 0)))

        return addr, size

    def __init__(self, region=None, addr=None, size=None, align=None):
        region = Region.parseregion(region) if region else (None, None)
        self.align = align
        self.addr = addr if addr is not None else region[0]
        self.size = size if size is not None else region[1] or 0

        assert self.size >= 0, "Invalid region size %#x?" % self.size
        if self.align and self.addr:
            assert self.addr % self.align == 0, ("Region address %#010x "
                "not aligned to region alignment %#010x" % (
                    self.addr, self.align))
        if self.align:
            assert self.size % self.align == 0, ("Region size %#010x "
                "not aligned to region alignment %#010x" % (
                    self.size, self.align))

    def __str__(self):
        return "%(range)s %(size)d bytes" % dict(
            range='%#010x-%#010x' % (self.addr, self.addr+self.size-1)
                if self.addr is not None else
                '%#010x' % self.size,
            size=self.size)

    def __bool__(self):
        return bool(self.size)

    def __lt__(self, other):
        return self.addr < other.addr

    def __contains__(self, other):
        if isinstance(other, Region):
            return (other.addr >= self.addr and
                other.addr+other.size <= self.addr+self.size)
        else:
            return (other >= self.addr and
                other < self.addr + self.size)

    def __sub__(self, regions):
        if isinstance(regions, Region):
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

        return [Region(addr=self.addr, size=self.size)
            for addr, size in slices]

class Memory(Region):
    """
    Description of a memory region named MEMORY.
    """
    MODEFLAGS = ['r', 'w', 'x']

    __argname__ = "memory"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser, **kwargs):
        parser.add_argument("memory", pred=cls.parsememory,
            help=cls.__arghelp__)
        parser.add_argument("--mode", pred=cls.parsemode,
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

        return mode, addr, size

    def __init__(self, name, memory=None,
            mode=None, addr=None, size=None, align=None):
        self.name = name
        memory = Memory.parsememory(memory) if memory else (None, None, None)
        self.mode = Memory.parsemode(mode) if mode else memory[0] or set()
        self.align = align
        self.addr = addr if addr is not None else memory[1]
        self.size = size if size is not None else memory[2] or 0

        assert self.size >= 0, "Invalid memory size %#x?" % self.size
        if self.align and self.addr:
            assert self.addr % self.align == 0, ("Memory address %#010x "
                "not aligned to memory alignment %#010x" % (
                    self.addr, self.align))
        if self.align:
            assert self.size % self.align == 0, ("Memory size %#010x "
                "not aligned to memory alignment %#010x" % (
                    self.size, self.align))

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

    def __lt__(self, other):
        return (self.addr, self.name) < (other.addr, other.name)

    def consume(self, addr=None, size=None, align=None, section=None,
            reverse=False):
        if section is not None:
            size = section.size
            align = section.align
        if size is None:
            addr, size = None, addr or 0
        #assert addr is None, "TODO" # TODO
        addr = None # TODO HACK
        assert align is None, "TODO" # TODO
        assert size <= self._size, ("Not enough memory in %s "
            "for size=%#010x" % (self.name, size))

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
            align=None, name=None, section=None):
        if section is not None:
            size = section.size
            align = section.align
            name = section.memory
        if size is None:
            addr, size = None, addr
        #assert addr is None, "TODO" # TODO
        addr = None # TODO HACK
        assert align is None, "TODO" # TODO
        return (
            self._size != 0 and
            set(mode).issubset(self.mode) and
            (size is None or size <= self._size) and
            (name is None or name == self.name))

    @staticmethod
    def compatiblekey(mode='rwx', addr=None, size=None,
            align=None, reverse=False, section=None):
        if section is not None:
            size = section.size
            align = section.align
            name = section.memory
        if size is None:
            addr, size = None, addr
        #assert addr is None, "TODO" # TODO
        addr = None # TODO HACK
        assert align is None, "TODO" # TODO
        def key(self):
            return (
                len(self.mode - set(mode)),
                -self.addr if reverse else self.addr)
        return key

    def __sub__(self, regions):
        if isinstance(regions, Region):
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


class Type:
    """
    Type of function argument or return value.
    """
    PRIMITIVE_TYPES = [
        'err32', 'err64',
        'u8', 'u16', 'u32', 'u64', 'usize',
        'i8', 'i16', 'i32', 'i64', 'isize',
        'f32', 'f64']
    PRIMITIVE_ALIASES = [
        (r'\berr\b',            r'err32'),
        (r'\bu\b',              r'u32'),
        (r'\bi\b',              r'i32'),
        (r'\buint(\d+)_t\b',    r'u\1'),
        (r'\bint(\d+)_t\b',     r'i\1'),
        (r'\bsize_t\b',         r'usize'),
        (r'\bssize_t\b',        r'isize'),
        (r'\bfloat\b',          r'f32'),
        (r'\bdouble\b',         r'f64'),
        (r'\bvoid *\*',         r'u8*')]
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

    def isptr(self):
        return bool(self._ptr)

    def iserr(self):
        return self._primitive.startswith('err')

    def __str__(self, argname=None):
        if argname:
            return '%s %s%s' % (self._primitive, self._ptr, argname)
        else:
            return '%s%s' % (self._primitive, self._ptr)

    def repr_c(self, name=None):
        if self._primitive == 'u8' and self._ptr:
            primitive = 'void'
        if self._primitive.startswith('err'):
            primitive = 'int%s_t' % self._primitive[3:]
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
            assert False, 'unknown type %r' % self._primitive

        if name:
            return '%s %s%s' % (primitive, self._ptr, name)
        else:
            return '%s%s' % (primitive, self._ptr)

class Fn:
    """
    Function type.
    """
    @classmethod
    def __argparse__(cls, parser, **kwargs):
        parser.add_argument("type", pred=cls.parsetype,
            help=cls.__arghelp__)
        parser.add_argument("--type", pred=cls.parsetype,
            help="Type of the function.")
        parser.add_argument("--doc",
            help="Docstring for the function.")

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
            raise ValueError("Currently only 0 or 1 return values supported")

        return args, argnames, rets, retnames

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

    def isfalible(self):
        return any(ret.iserr() for ret in self.rets)

class Import(Fn):
    """
    Description of an imported function for a box.
    """
    __argname__ = "import"
    __arghelp__ = __doc__

class Export(Fn):
    """
    Description of an exported function for a box.
    """
    __argname__ = "export"
    __arghelp__ = __doc__

class Box:
    """
    Recursive description of a given box named BOX.
    """
    __argname__ = "box"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser, recursive=False, fake=False, **kwargs):
        parser.add_argument('--name',
            help='Name of the box.')
        parser.add_argument('--path',
            help='Working directory for the box. Defaults to the '
                'name of the box.')
        parser.add_argument('--recipe',
            help='Path to reciple.toml file for box-specific configuration.'
                'Defaults to <path>/recipe.toml.')

        from .runtimes import RUNTIMES
        runtimeparser = parser.add_nestedparser('--runtime')
        runtimeparser.add_argument("select",
            metavar='RUNTIME', choices=RUNTIMES,
            help='Runtime for the box. This can be one of the following '
                'runtimes: {%(choices)s}.')
        runtimeparser.add_argument("--select",
            metavar='RUNTIME', choices=RUNTIMES,
            help='Runtime for the box. This can be one of the following '
                'runtimes: {%(choices)s}.')
        for Runtime in RUNTIMES.values():
            runtimeparser.add_nestedparser(Runtime)

        from .outputs import OUTPUTS
        outputparser = parser.add_nestedparser('--output')
        for Output in OUTPUTS.values():
            outputparser.add_nestedparser(Output)

        parser.add_set(Memory)
        parser.add_nestedparser('--stack', Section)
        parser.add_nestedparser('--heap', Section)
        parser.add_nestedparser('--text', Section)
        parser.add_nestedparser('--data', Section)
        parser.add_nestedparser('--bss', Section)

        parser.add_set(Import, dest='import_')
        parser.add_set(Export)

    def __init__(self, name=None, parent=None, path=None, recipe=None,
            runtime=None, output=None, memory=None,
            stack=None, heap=None, text=None, data=None, bss=None,
            import_=None, export=None, box=None):
        self.name = name or 'system'
        self.parent = parent
        self.path = path
        self.recipe = recipe

        from .runtimes import RUNTIMES
        selected = runtime.select or 'noop'
        self.runtime = RUNTIMES[selected](**getattr(
            runtime, selected).__dict__)

        from .outputs import OUTPUTS
        self.outputs = sorted(
            OUTPUTS[name](os.path.join(self.path, outputargs.path),
                **{k: v for k, v in outputargs.__dict__.items()
                    if k != 'path'})
            for name, outputargs in output.__dict__.items()
            if outputargs.path)

        self.memories = sorted(
            Memory(name, **memargs.__dict__)
            for name, memargs in memory.items())

        self.stack = Section(**stack.__dict__)
        self.heap = Section(**heap.__dict__)
        self.text = Section(**text.__dict__)
        self.data = Section(**data.__dict__)
        self.bss = Section(**bss.__dict__)

        self.imports = sorted(
            Import(name, **importargs.__dict__)
            for name, importargs in import_.items())
        self.exports = sorted(
            Import(name, **exportargs.__dict__)
            for name, exportargs in export.items())
        self.boxes = [] 

        # prepare build/box commands for prologue/epilogue handling
        self.box_prologues = co.OrderedDict()
        self.box_epilogues = co.OrderedDict()
        self.build_prologues = co.OrderedDict()
        self.build_epilogues = co.OrderedDict()

    def __eq__(self, other):
        return self.name == other.name

    def __lt__(self, other):
        return self.name < other.name

    def bestmemories(self, mode='rwx', addr=None, size=None,
            align=None, name=None, section=None, reverse=False):
        if section:
            size = section.size
            align = section.align
            name = section.memory
        if size is None:
            addr, size = None, addr
        return sorted((
                m for m in self.memories
                if m.compatible(mode=mode, addr=addr, size=size,
                    align=align, name=name)),
            key=Memory.compatiblekey(mode=mode, addr=addr, size=size,
                align=align, section=section, reverse=reverse))

    def bestmemory(self, mode='rwx', addr=None, size=None,
            align=None, name=None, section=None, reverse=False):
        if section:
            size = section.size
            align = section.align
            name = section.memory
        if size is None:
            addr, size = None, addr
        compatible = self.bestmemories(mode=mode, addr=addr, size=size,
            align=align, name=name, section=section, reverse=reverse)
        return compatible[0] if compatible else None

    def consume(self, mode='rwx', size=None, addr=None,
            align=None, name=None, section=None, reverse=False):
        if section:
            size = section.size
            align = section.align
            name = section.memory
        if size is None:
            addr, size = None, addr
        best = self.bestmemory(mode=mode, addr=addr, size=size,
            align=align, name=name, section=section, reverse=reverse)
        assert best, "No memory found that satisfies mode=%s size=%#010x" % (
            mode, size)
        addr, size = best.consume(addr=addr, size=size,
            align=align, section=section, reverse=reverse)
        return best, addr, size

    def getroot(self):
        """
        Get the root box of the current tree.
        """
        root = self
        while root.parent:
            root = root.parent
        return root if root != self else None

    def getmuxer(self):
        """
        Returns the muxer box of the current runtime. This is defined to be
        nearest parent that is a different runtime. This is the point where
        tree muxing must be done.
        """
        muxer = self
        while muxer.parent and muxer.runtime == self.runtime:
            muxer = muxer.parent
        return muxer if muxer != self else None

    def getparent(self, n=1):
        """
        Returns a box's nth parent, if it has an nth parent.
        """
        parent = self
        for _ in range(n):
            if not self.parent:
                return None
            parent = self.parent
        return parent if parent != self else None

    @staticmethod
    def _scan_argparse(parser):
        # add root box
        Box.__argparse__(parser)
        # add nested boxes
        parser.add_set(Box, glob=True, action='append',
            help='Recursive description of a given box named BOX that is '
                'contained in the current box.')
        parser.add_set('--super', cls=Box, glob=True, action='append',
            help='Recursive description of superboxes. These are boxes '
                'that contain the current box. Note, each box can only have '
                'one superbox, however that superbox can have other boxes.')
        # also add a shortcut for providing box defaults
        parser.add_nestedparser('--all', cls=Box, glob=True,
            help='Alias for all boxes. This allows you to specify config '
                'that all boxes inherit unless explicitly overwritten.')

    @staticmethod
    def scan(name=None, **args):
        """
        Build up tree of config information for boxes. This handles box
        creation and reading recipe.json files from the filesystem. Tree
        is rotated so superbox is returned, even if it's not located in the
        current directory.
        """
        # prepare parser
        parser = ArgumentParser(add_help=False)
        Box.scan.__argparse__(parser)

        def recurse(prefix=None, parent=None, child=None,
                parentallargs=argstuff.Namespace(), **args):
            # reparse
            args = parser.parse_dict(args, prefix=prefix)

            # load additional config from the filesystem
            path = args.path or '.'
            recipe = args.recipe or 'recipe.toml'
            try:
                nargs = parser.parse_toml(os.path.join(path, recipe),
                    prefix=prefix)
                args = argstuff.nsmerge(args, nargs)
            except FileNotFoundError:
                pass

            # apply all
            allargs = parser.parse_dict(args.all)
            allargs = argstuff.nsmerge(parentallargs, allargs)
            args = argstuff.nsmerge(allargs, args)

            # create the box!
            # note that name may be in recipe.toml (root only)
            box = Box(args.name, path=path, recipe=recipe, **{
                k: v for k, v in args.__dict__.items()
                if k not in {
                    'name', 'path', 'recipe', 'boxes', 'super', 'all'}})

            # scan parent/children
            if parent:
                assert not args.super, (
                    "Child box can't have parent (%s)" % box.name)
                box.parent = parent
            elif args.super:
                assert len(args.super) == 1, (
                    "A box can only have one superbox (%s)" %
                        ', '.join(args.super.keys()))
                name, boxargs = next(iter(args.super.items()))
                # create parent
                box.parent = recurse(**{**boxargs.__dict__, **dict(
                    name=name,
                    prefix=(prefix or '--') + 'super.%s.' % name,
                    path=os.path.join(path,
                        getattr(boxargs, 'path', None) or name),
                    child=box,
                    parentallargs=allargs)})

            boxes = []
            if child:
                assert all(name != child.name for name in args.box.items()), (
                    "Parent box can't have child with same name (%s)" % name)
                boxes.append(child)
            for name, boxargs in sorted(args.box.items()):
                # create child
                boxes.append(recurse(**{**boxargs.__dict__, **dict(
                    name=name,
                    prefix=(prefix or '--') + 'boxes.%s.' % name,
                    path=os.path.join(path,
                        getattr(boxargs, 'path', None) or name),
                    parent=box,
                    parentallargs=allargs)}))
            box.boxes = sorted(boxes)

            return box

        box = recurse(name, **args)

        # unzip the box
        while box.parent:
            box = box.parent

        # go ahead and box the box, it's always needed 
        box.box()
        return box

    scan.__func__.__argparse__ = _scan_argparse.__func__

    def box(self, stage=None):
        """
        Apply any post-init configuration that needs to know the full
        tree of boxes.
        """
        if not stage or stage == 'boxes':
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
                box.box(stage='boxes')

        if not stage or stage == 'runtimes':
            self.runtime.box(self)
            for box in self.boxes:
                box.box(stage='runtimes')

        if not stage or stage == 'outputs':
            for output in self.outputs:
                output.box(self)
            for box in self.boxes:
                box.box(stage='outputs')

        if not stage or stage == 'epilogues':
            for box in self.boxes:
                box.build(stage='epilogues')
            for epilogue in self.build_epilogues.values():
                epilogue()

    def build(self, stage=None):
        """
        Generate output data based on configured runtimes and outputs.
        """
        if not stage or stage == 'runtimes':
            self.runtime.build(self)
            for box in self.boxes:
                box.build(stage='runtimes')

        if not stage or stage == 'outputs':
            for box in self.boxes:
                box.build(stage='outputs')
            for output in self.outputs:
                output.build(self)

        if not stage or stage == 'epilogues':
            for box in self.boxes:
                box.build(stage='epilogues')
            for epilogue in self.build_epilogues.values():
                epilogue()
