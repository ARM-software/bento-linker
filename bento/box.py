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
        addrpattern = r'(?:0[oxb])?[0-9a-fA-F]+'
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

    def __init__(self, name, size=None, align=None, memory=None):
        self.name = name
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
        return self.size is not None

    def alloc(self, box, mode='rwxp', reverse=False):
        """
        Find best memory given parameters and assign this section to it.
        This updates Section's memory field as well as adds ourselfe to
        the Memory's list of sections.
        """
        memory = box.consume(mode,
            size=self.size,
            align=self.align,
            memory=self.memory,
            reverse=reverse)
        assert memory is not None, (
            "Not enough memory found that satisfies mode=%s size=%d:\n"
            "%s\n"
            "%s = %s in %s\n"
            "%s" % (
            ''.join(mode), self.size or 0,
            '\n'.join("%s = %s in %s" % (
                section.name, section, box.name)
                for memory in box.memoryslices
                if set(mode).issubset(memory.mode)
                for section in memory.sections
                if section),
            self.name, self, box.name,
            '\n'.join("memory.%s = %s in %s" % (
                memory.name, memory, box.name)
                for memory in box.memoryslices)))

        memory.sections.append(self)
        self.memory = memory
        return memory

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
        parser.add_argument("--region", pred=cls.parseregion,
            help=cls.__arghelp__)
        parser.add_argument("--addr", type=lambda x: int(x, 0),
            help="Starting address of region. Note that addr may be "
                "undefined if the exact location does not matter.")
        parser.add_argument("--size", type=lambda x: int(x, 0),
            help="Size of the region in bytes.")

    @staticmethod
    def parseregion(s):
        addrpattern = r'(?:0[oxb])?[0-9a-fA-F]+'
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

    def __init__(self, region=None, addr=None, size=None):
        region = Region.parseregion(region) if region else (None, None)
        self.addr = addr if addr is not None else region[0]
        self.size = size if size is not None else region[1] or 0
        assert self.size >= 0, "Invalid region size %#x?" % self.size

    def __str__(self):
        return "%(range)s %(size)d bytes" % dict(
            range='%#010x-%#010x' % (self.addr, self.addr+self.size-1)
                if self.addr is not None else
                '%#010x' % self.size,
            size=self.size)

    def __bool__(self):
        return self.size is not None

    def __lt__(self, other):
        return self.addr < other.addr

    def __contains__(self, other):
        if isinstance(other, Region):
            return (other.addr >= self.addr and
                other.addr+other.size <= self.addr+self.size)
        else:
            return (other >= self.addr and
                other < self.addr + self.size)

    def overlaps(self, other):
        return (self.addr < other.addr+other.size and
            self.addr+self.size > other.addr)

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

        return [Region(addr=addr, size=size) for addr, size in slices]

class Memory(Region):
    """
    Description of a memory region named MEMORY.
    """
    MODEFLAGS = ['r', 'w', 'x', 'p']

    __argname__ = "memory"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser, **kwargs):
        parser.add_argument("memory", pred=cls.parsememory,
            help=cls.__arghelp__)
        parser.add_argument("--memory", pred=cls.parsememory,
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
        mode = set(s) - {'-'}
        if not mode.issubset(set(Memory.MODEFLAGS)):
            raise ValueError("invalid memory mode %r" % s)
        return mode

    @staticmethod
    def parsememory(s):
        addrpattern = r'(?:0[oxb])?[0-9a-fA-F]+'
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
        self.name = name.name if isinstance(name, Memory) else name
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
        self.sections = name.sections if isinstance(name, Memory) else []
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
        return (self.addr or 0, self.name) < (other.addr or 0, other.name)

    def used(self):
        return self.size - self._size

    def unused(self):
        return self._size

    def consume(self, size=None, align=None, reverse=False):
        assert align is None, "TODO" # TODO
        assert size <= self._size, ("Not enough memory in %s "
            "for size=%#010x" % (self.name, size))

        if not reverse:
            self._addr += size
            self._size -= size
            return Memory(self, mode=self.mode,
                addr=self._addr, size=size, align=None)
        else:
            self._size -= size
            return Memory(self, mode=self.mode,
                addr=self._addr + self._size, size=size, align=None)

    def iscompatible(self, mode='rwxp', size=None, align=None, memory=None):
        if isinstance(memory, Memory):
            memory = memory.name
        assert align is None, "TODO" # TODO
        return (
            self._size != 0 and
            set(mode).issubset(self.mode) and
            (memory is None or memory == self.name) and
            (size is None or size <= self._size))

    @staticmethod
    def keybest(mode='rwxp', size=None, align=None, memory=None,
            reverse=False):
        def key(self):
            return (
                len(self.mode - set(mode)),
                -self.addr if reverse else self.addr)
        return key

    def __sub__(self, regions):
        return [
            Memory(self.name, mode=self.mode, align=self.align,
                addr=region.addr, size=region.size)
            for region in super().__sub__(regions)]

class Arg:
    """
    Type of function argument or return value.
    """
    MODIFIERS = ['const', 'mut', 'nullable']
    PRIMITIVES = [
        'bool',
        'u8', 'u16', 'u32', 'u64', 'usize',
        'i8', 'i16', 'i32', 'i64', 'isize',
        'f32', 'f64',
        'err', 'err8', 'err16', 'err32', 'err64', 'errsize']
    @staticmethod
    def parsetype(s):
        namepattern = r'[a-zA-Z_][a-zA-Z_0-9]*'
        numpattern = r'(?:0[oxb])?[0-9a-fA-F]+'
        modpattern = r'(?:(?:%s)\b\s*)*' % '|'.join(Arg.MODIFIERS)
        primpattern = r'(?:%s)\b' % '|'.join(Arg.PRIMITIVES)
        arraypattern = (r'\s*'.join([
            r'\[',
                r'(?:(%(name)s)|(%(num)s))',
            r'\]']) % dict(
                name=namepattern,
                num=numpattern))
        ptrpattern = (r'\s*'.join([
            r'(?:',
                r'\*',
            r'|',
                r'%(array)s'
            r')*']) % dict(
                array=arraypattern))
        argpattern = (r'\s*'.join([
            r'(?:', r'(%(name)s)', r':', r')?'
            r'(%(mod)s)',
            r'(%(prim)s)',
            r'(%(ptr)s)',
            r'(%(name)s)?',
            r'(%(ptr)s)']) % dict(
                name=namepattern,
                num=numpattern,
                mod=modpattern,
                prim=primpattern,
                ptr=ptrpattern))

        m = re.match(r'^\s*%s\s*$' % argpattern, s)
        if not m:
            raise ValueError("Invalid type %r" % s)
        if m.group(1) and m.group(7):
            raise ValueError("Duplicate names in type %r?" % s)

        mod   = set(m.group(2).split()) or set()
        prim  = m.group(3)
        name  = m.group(1) or m.group(7) or None
        ptr   = ''.join(c for c in m.group(4) + m.group(8) if c == '*')
        asize = (m.group(5)
            if m.group(5) else
            int(m.group(6), 0)
            if m.group(6) else
            m.group(9)
            if m.group(9) else
            int(m.group(10), 0)
            if m.group(10) else
            None)

        return name, mod, prim, ptr, asize

    def __init__(self, name, type=None):
        if type is None:
            name, type = None, name

        name2, mod, prim, ptr, asize = self.parsetype(type)

        if ptr and len(ptr) > 1:
            raise ValueError(
                "Indirect pointers currently unsupported %r" % type)

        if mod and not (ptr or asize):
            raise ValueError(
                "Unexpected modifier %r" % type)

        if (ptr or asize) and not {'const', 'mut'} & mod:
            raise ValueError(
                "Pointers must have const/mut modifiers %r" % type)

        if {'const', 'mut'}.issubset(mod):
            raise ValueError(
                "Too many const/mut modifiers %r" % type)

        self._mod   = mod
        self._prim  = prim
        self._ptr   = ptr
        self._asize = asize

        self.name = name or name2 or None
        self.type = self.__str__(name='')

    def ismut(self):
        return 'mut' in self._mod

    def isconst(self):
        return 'const' in self._mod

    def isnullable(self):
        return 'nullable' in self._mod

    def isptr(self):
        return bool(self._ptr or self._asize)

    def isarray(self):
        return bool(self._asize)

    def iserr(self):
        return self._prim.startswith('err') and not self.isptr()

    def prim(self):
        return self._prim

    def primwidth(self):
        # TODO configurable ptr width?
        return (
            8  if self._prim in {'i8', 'u8', 'bool'} else
            16 if self._prim in {'i16', 'u16'} else
            64 if self._prim.endswith('64') else
            32)

    def primsize(self):
        return (self.primwidth() // 8) if self.primwidth() > 32 else 4

    def width(self):
        # TODO configurable ptr width?
        return 32 if self.isptr() else self.primwidth()

    def size(self):
        return (self.width() // 8) if self.width() > 32 else 4

    def asize(self):
        return self._asize

    def __eq__(self, other):
        return ((self._mod, self._prim, self._ptr,
                self._asize if isinstance(self._asize, int) else 'dyn')
            == (other._mod, other._prim, other._ptr,
                other._asize if isinstance(other._asize, int) else 'dyn'))

    def __str__(self, name=None):
        name = name if name is not None else self.name
        return ''.join([
            '%s ' % ' '.join(self._mod) if self._mod else '',
            self._prim,
            ' ' if name else '',
            self._ptr or '',
            name if name else '',
            '[%s]' % self._asize if self._asize else ''])

class Link:
    """
    Simple tuple for connecting functions.
    """
    def __init__(self, export, import_):
        self.export = export
        self.import_ = import_

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
        parser.add_argument("--scope", underscore=True,
            help="Box to limit import/export access to.")
        parser.add_argument("--alias", underscore=True,
            help="Name used in the box for the function.")
        parser.add_argument("--doc",
            help="Documentation for the function.")

    @staticmethod
    def parsetype(s):
        namepattern = r'[a-zA-Z_][a-zA-Z_0-9]*'
        argpattern = (r'(?:(?:%(name)s|[:\*\[\]0-9])\s*)+'
            % dict(name=namepattern))
        # functions with and without parens around args/rets
        fnpattern = (r'\s*'.join([
            r'fn',
            r'(?:',
                r'\(',
                r'((?:%(arg)s', r'(?:', r',', r'%(arg)s', r')*)?)',
                r',?',
                r'\)',
            r'|',
                r'((?:%(arg)s', r'(?:', r',', r'%(arg)s', r')*)?)',
                r',?',
            r')',
            r'->',
            r'(?:',
                r'\(',
                r'((?:%(arg)s', r'(?:', r',', r'%(arg)s', r')*)?)',
                r',?',
                r'\)',
            r'|',
                r'((?:%(arg)s', r'(?:', r',', r'%(arg)s', r')*)?)',
                r',?',
            r')']) % dict(
                name=namepattern,
                arg=argpattern))

        m = re.match('^\s*%s\s*$' % fnpattern, s)
        if not m:
            raise ValueError("Invalid import/export type %r" % s)

        noreturn = False
        args = [arg.strip() for arg in
            (m.group(1) or m.group(2) or '').split(',')]
        rets = [ret.strip() for ret in
            (m.group(3) or m.group(4) or '').split(',')]
        if rets == ['noreturn']:
            noreturn = True
            rets = []
        if args in [['void'], ['']]:
            args = []
        if rets in [['void'], ['']]:
            rets = []

        try:
            for arg in it.chain(args, rets):
                Arg.parsetype(arg)
        except ValueError as e:
            e.args = (e.args[0]+'\nWhile parsing %r' % s, *e.args[1:])
            raise

        return args, rets, noreturn

    def __init__(self, name, type=None, source=None, scope=None,
            alias=None, doc=None, weak=False):
        if type is None:
            name, type = None, name

        args, rets, noreturn = self.parsetype(type)

        args = [Arg(arg) for arg in args]
        rets = [Arg(ret) for ret in rets]

        if sum(arg.size() for arg in args) > 4*4:
            raise ValueError("Currently only 0-4 arguments are supported")
        if len(rets) > 1:
            raise ValueError("Currently only 0 or 1 return values supported")

        names = set()
        for arg in it.chain(args, rets):
            if arg.name:
                if arg.name in names:
                    raise ValueError("Arg %r not unique in %r" % (
                        arg.name, type))
                names.add(arg.name)
        for arg in args:
            if isinstance(arg.asize(), str):
                if not any(arg2.name == arg.asize() for arg2 in args):
                    raise ValueError("No arg matches array size for %r" % type)
        for ret in rets:
            if isinstance(ret.asize(), str):
                raise ValueError("Returning buffers with dependent sizes "
                    "currently not supported %r" % type)

        if scope is None and '.' in name:
            self.scope, self.name = name.split('.', 1)
        else:
            self.name = name
            self.scope = scope
        self.scopedname = '.'.join(filter(None, [self.scope, self.name]))

        self.args = args
        self.rets = rets
        self._noreturn = noreturn

        self.alias = alias or self.name
        self.doc = doc
        self.weak = weak

        assert source is not None, "Need a source you doofus (internal error)"
        self.source = source

    def __str__(self):
        return 'fn(%s) -> %s' % (
            ', '.join(map(str, self.args)),
            'noreturn' if self.isnoreturn() else
            'void' if not self.rets else
            ', '.join(map(str, self.rets)))

    def reprcontext(self, direction):
        return ('%(direction)s.%(name)s = '
            '%(type)s in %(source)s%(scope)s' % dict(
            direction=direction,
            name=self.name,
            type=str(self),
            source=self.source,
            scope=' (scope=%s)' % self.scope if self.scope else ''))

    def __lt__(self, other):
        return self.name < other.name

    def uniquename(self, name):
        """ Insure name is unique given arg/rets """
        if any(arg.name == name for arg in it.chain(self.args, self.rets)):
            return '__box_' + name
        else:
            return name

    def argnames(self):
        names = set(
            arg.name for arg in it.chain(self.args, self.rets)
            if arg.name)
        for i, arg in enumerate(self.args):
            if arg.name:
                yield arg.name
            else:
                # try nice looking argname
                name = 'a%d' % i
                if name not in names:
                    yield name
                else:
                    # fallback to this ugly (but unique!) name
                    yield '__box_' + name

    def retnames(self):
        names = set(
            arg.name for arg in it.chain(self.args, self.rets)
            if arg.name)
        for i, arg in enumerate(self.rets):
            if arg.name:
                yield arg.name
            else:
                # try nice looking argname
                name = 'r%d' % i
                if name not in names:
                    yield name
                else:
                    # fallback to this ugly (but unique!) name
                    yield '__box_' + name

    def retname(self):
        return next(it.chain(self.retnames(), ['__r0']))

    def isnoreturn(self):
        return self._noreturn

    def isfalible(self):
        return any(ret.iserr() for ret in self.rets)

    def iscompatible(self, other):
        anames = {arg.name: i for i, arg in enumerate(self.args) if arg.name}
        bnames = {arg.name: i for i, arg in enumerate(other.args) if arg.name}
        for a, b in zip(
                it.chain(self.args, self.rets),
                it.chain(other.args, other.rets)):
            # check that types are equivalent?
            if a != b:
                return False

            # check that array references are in the correct places
            if isinstance(a.asize(), str):
                if anames[a.asize()] != bnames[b.asize()]:
                    return False

        return True

    def islinkable(self, other, exportbox=None, importbox=None):
        return (self.name == other.name and 
            (self.scope is None or
                exportbox is None or
                self.scope == exportbox) and
            (other.scope is None or
                importbox is None or
                other.scope == importbox))

class Import(Fn):
    """
    Description of an imported function for a box.
    """
    __argname__ = "import"
    __arghelp__ = __doc__
    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        # these get populated later
        self.box = None
        self.link = None

    def reprcontext(self, direction='import'):
        return super().reprcontext(direction)

class Export(Fn):
    """
    Description of an exported function for a box.
    """
    __argname__ = "export"
    __arghelp__ = __doc__
    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        # these get populated later
        self.box = None
        self.links = []

    def reprcontext(self, direction='export'):
        return super().reprcontext(direction)

class Box:
    """
    Recursive description of a given box named BOX.
    """
    __argname__ = "box"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser, recursive=False, fake=False, **kwargs):
        parser.add_argument('--path',
            help='Working directory for the box. Defaults to the '
                'name of the box.')
        parser.add_argument('--recipe',
            help='Path to reciple.toml file for box-specific configuration. '
                'Defaults to <path>/recipe.toml.')
        parser.add_argument('--name', underscore=True,
            help='Name of the box. Only valid for the top-level box.')

        from .runtimes import RUNTIMES
        runtimeparser = parser.add_nestedparser('--runtime')
        runtimeparser.add_argument("runtime",
            metavar='RUNTIME', choices=RUNTIMES, underscore=True,
            help='Runtime for the box. This can be one of the following '
                'runtimes: {%(choices)s}.')
        runtimeparser.add_argument("--runtime",
            metavar='RUNTIME', choices=RUNTIMES, underscore=True,
            help='Runtime for the box. This can be one of the following '
                'runtimes: {%(choices)s}.')
        for Runtime in RUNTIMES.values():
            runtimeparser.add_nestedparser(Runtime)

        from .loaders import LOADERS
        loaderparser = parser.add_nestedparser('--loader')
        loaderparser.add_argument("loader",
            metavar='LOADER', choices=LOADERS, underscore=True,
            help='Loader for the box. This can be one of the following '
                'loaders: {%(choices)s}. Defaults to noop.')
        loaderparser.add_argument("--loader",
            metavar='LOADER', choices=LOADERS, underscore=True,
            help='Loader for the box. This can be one of the following '
                'loaders: {%(choices)s}. Defaults to noop.')
        for Loader in LOADERS.values():
            loaderparser.add_nestedparser(Loader)

        parser.add_argument('--init', choices=['lazy', 'manual'],
            help='Select when the box will be initialized. \'lazy\' init will '
                'initialize the box on the first box call, at the cost of some '
                'overhead on every call. \'manual\' leaves it up to the user '
                'to call __box_<name>_init() manually. Must be one of: '
                '{%(choices)s}. Defaults to lazy.')
        parser.add_argument('--idempotent', type=bool,
            help='Indicate if the box is idempotent, where idempotency '
                'indicates if it is ok to lose state between box calls. '
                'Idempotent boxes can share RAM with a performance penalty. '
                'Defaults to false.')

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

        parser.add_set(Import)
        parser.add_set(Import, metavar='BOX.IMPORT', depth=2)
        parser.add_set(Export)
        parser.add_set(Export, metavar='BOX.EXPORT', depth=2)

    def __init__(self, name=None, parent=None, path=None, recipe=None,
            runtime=None, loader=None, init=None, idempotent=None,
            output=None, debug=None, lto=None,
            srcs=None, incs=None, define={},
            memory=None, stack=None, heap=None,
            text=None, data=None, bss=None,
            export={}, box={}, **kwargs):
        self.name = name or 'sys'
        self.parent = parent
        self.path = path
        self.recipe = recipe

        from .runtimes import RUNTIMES
        assert runtime.runtime, "No runtime specified for box `%s`" % self.name
        selected = runtime.runtime
        self.runtime = RUNTIMES[selected](**getattr(
            runtime, selected, argstuff.Namespace()).__dict__)

        from .loaders import LOADERS
        selected = loader.loader or 'noop'
        self.loader = LOADERS[selected](**getattr(
            loader, selected, argstuff.Namespace()).__dict__)

        self.init = (init if init is not None else 'lazy')
        self.idempotent = (
            idempotent if idempotent is not None else False)
        self.roommates = []

        from .outputs import OUTPUTS
        self.outputs = sorted(
            OUTPUTS[name](os.path.join(self.path, outputargs.path),
                **{k: v for k, v in outputargs.__dict__.items()
                    if k != 'path'})
            for name, outputargs in output.__dict__.items()
            if outputargs.path)

        # build the runtime stack
        from .outputs import OutputGlue
        self.loader.inherit(OutputGlue())
        self.runtime.inherit(self.loader)

        self.memories = sorted(
            Memory(name, **memargs.__dict__)
            for name, memargs in memory.items())
        self.memoryslices = self.memories

        self.stack = Section('stack', **stack.__dict__)
        self.heap = Section('heap', **heap.__dict__)
        self.text = Section('text', **text.__dict__)
        self.data = Section('data', **data.__dict__)
        self.bss = Section('bss', **bss.__dict__)

        self.imports = sorted(
            Import(name, source=self.name, **importargs.__dict__)
            for name, importargs in it.chain.from_iterable(
                [('%s.%s' % (k, k2), v2) for k2, v2 in v.items()]
                if isinstance(v, dict) else
                [(k, v)]
                for k, v in kwargs.get('import', {}).items())
            if importargs is not None)
            # TODO probably look into this last condition

        self.exports = sorted(
            Export(name, source=self.name, **exportargs.__dict__)
            for name, exportargs in it.chain.from_iterable(
                [('%s.%s' % (k, k2), v2) for k2, v2 in v.items()]
                if isinstance(v, dict) else
                [(k, v)]
                for k, v in export.items())
            if exportargs is not None)
            # TODO probably look into this last condition

        self.boxes = [] 

    def __eq__(self, other):
        if isinstance(other, Box):
            return self.name == other.name
        else:
            return self.name == other

    def __lt__(self, other):
        return self.name < other.name

    def bestmemories(self, mode='rwxp', size=None, align=None, memory=None,
            reverse=False):
        constraints = dict(
            mode=set(mode),
            size=size,
            align=align,
            memory=memory.name if isinstance(memory, Memory) else memory)
        self.loader.constraints(constraints)
        mode   = constraints.get('mode', None)
        size   = constraints.get('size', None)
        align  = constraints.get('align', None)
        memory = constraints.get('memory', None)

        return sorted((
                m for m in self.memoryslices
                if m.iscompatible(mode=mode,
                    size=size, align=align, memory=memory)),
            key=Memory.keybest(mode=mode,
                size=size, align=align, memory=memory,
                reverse=reverse))

    def bestmemory(self, mode='rwxp', size=None, align=None, memory=None,
            reverse=False):
        compatible = self.bestmemories(mode=mode,
            size=size, align=align, memory=memory,
            reverse=reverse)
        return compatible[0] if compatible else None

    def consume(self, mode='rwxp', size=None, align=None, memory=None,
            reverse=False):
        best = self.bestmemory(mode=mode,
            size=size, align=align, memory=memory,
            reverse=reverse)
        if best is None:
            return None

        return best.consume(size=size, align=align, reverse=reverse)

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

    def addimport(self, import_, *args, **kwargs):
        if not isinstance(import_, Export):
            import_ = Import(import_, *args, **kwargs)
        self.imports.append(import_)
        return import_

    def addexport(self, export, *args, **kwargs):
        if not isinstance(export, Export):
            export = Export(export, *args, **kwargs)
        self.exports.append(export)
        return export

    def pushattrs(self, **kwargs):
        """
        Push attrs across all outputs.
        """
        for output in self.outputs:
            output.pushattrs(**kwargs)

        class context:
            def __enter__(_):
                return self
            def __exit__(*_):
                self.popattrs()
        return context()

    def popattrs(self):
        """
        Pop attrs across all outputs.
        """
        for output in self.outputs:
            output.popattrs()

    @staticmethod
    def _scan_argparse(parser, **kwargs):
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
            assert os.path.isdir(path), "Path %r not found?" % path
            recipe = args.recipe or 'recipe.toml'
            try:
                nargs = parser.parse_toml(os.path.join(path, recipe),
                    prefix=prefix)
                args = argstuff.nsmerge(nargs, args)
            except FileNotFoundError:
                if args.recipe:
                    # raise if explicitly requested
                    raise
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

            if box.parent:
                assert all(child.name != box.parent.name
                    for child in box.boxes), (
                    "Conflicting names between box's parent/child `%s`" %
                    box.parent.name)

            return box

        box = recurse(name, **args)

        # unzip the box
        while box.parent:
            box = box.parent

        return box

    scan.__func__.__argparse__ = _scan_argparse.__func__

    def box(self, stage=None):
        """
        Apply any post-init configuration that needs to know the full
        tree of boxes.

        Needs to:
        - Allocate box memory
        - Allocate sections
        - Create implicit exports/imports
        """
        assert all(memory.addr is not None and
                memory.size is not None
                for memory in self.memoryslices), (
            "Memory insufficiently specified for box `%s`:\n%s" % (
                self.name,
                '\n'.join("memory.%s = %s in %s" % (
                    memory.name, memory, self.name)
                    for memory in self.memoryslices)))

        if not stage or stage == 'boxes':
            # create memory slices for children
            for child in self.boxes:
                for memory in child.memories:
                    if memory.addr is None:
                        slice = self.consume(
                            mode=memory.mode,
                            size=memory.size,
                            align=memory.align,
                            reverse=True)
                        assert slice is not None, (
                            "Not enough memory found that satisfies "
                            "mode=%s size=%d:\n"
                            "%s\n"
                            "%s" % (
                            ''.join(memory.mode), memory.size or 0,
                            '\n'.join("box.%s.memory.%s = %s in %s" % (
                                child.name, childmemory.name,
                                childmemory, self.name)
                                for child in self.boxes
                                for childmemory in child.memories
                                if memory.mode.issubset(childmemory.mode)
                                if childmemory),
                            '\n'.join("memory.%s = %s in %s" % (
                                memory.name, memory, self.name)
                                for memory in self.memoryslices)))

                        memory.addr = slice.addr
                        memory._addr = slice._addr

                    # check for overlaps
                    for child2 in self.boxes:
                        if child2.name == child.name:
                            continue
                        for memory2 in child2.memories:
                            if (memory2.addr is not None and
                                    memory2.overlaps(memory)):
                                assert (child.idempotent and
                                        child2.idempotent), (
                                    "Overlapping memory for non-idempotent "
                                    "boxes:\n"
                                    "memory.%s = %s in %s\n"
                                    "memory.%s = %s in %s" % (
                                    memory.name, memory, child.name,
                                    memory2.name, memory2, child2.name))
                                if child2 not in child.roommates:
                                    child.roommates.append(child2)

                    self.memoryslices = list(it.chain.from_iterable(
                        slice - memory for slice in self.memoryslices))

                # sort again in case new addresses changed order
                child.memories = sorted(child.memories)

            # make slice names unique
            namecount = {}
            for slice in self.memoryslices:
                namecount[slice.name] = namecount.get(slice.name, 0) + 1
            for name, count in namecount.items():
                if count > 1:
                    for i, slice in enumerate(
                            slice for slice in self.memoryslices
                            if slice.name == name):
                        slice.name = '%s%d' % (name, i+1)

            for child in self.boxes:
                child.box(stage='boxes')

        if not stage or stage == 'prologues':
            self._box_prologues = set()
            for level, suffix, relative in [
                    ('root', '_root', self.getroot()),
                    ('muxer', '_muxer', self.getmuxer()),
                    ('parent', '_parent', self.getparent()),
                    ('box', '', self)]:
                if not relative:
                    continue
                for output in relative.outputs:
                    if (level, output.name) not in relative._box_prologues:
                        getattr(self.runtime, 'box%s_%s_prologue' % (
                            suffix, output.name))(output, relative)
                        relative._box_prologues.add((level, output.name))
                if level not in relative._box_prologues:
                    getattr(self.runtime, 'box%s_prologue' % (
                        suffix))(relative)
                    relative._box_prologues.add(level)
            for child in self.boxes:
                child.box(stage='prologues')

        if not stage or stage == 'runtimes':
            for level, suffix, relative, *args in [
                    ('root', '_root', self.getroot(), self),
                    ('muxer', '_muxer', self.getmuxer(), self),
                    ('parent', '_parent', self.getparent(), self),
                    ('box', '', self)]:
                if not relative:
                    continue
                for output in relative.outputs:
                    getattr(self.runtime, 'box%s_%s' % (
                        suffix, output.name))(output, relative, *args)
                getattr(self.runtime, 'box%s' % (
                    suffix))(relative, *args)
            for child in self.boxes:
                child.box(stage='runtimes')

        if not stage or stage == 'epilogues':
            self._box_epilogues = set()
            for level, suffix, relative in [
                    ('root', '_root', self.getroot()),
                    ('muxer', '_muxer', self.getmuxer()),
                    ('parent', '_parent', self.getparent()),
                    ('box', '', self)]:
                if not relative:
                    continue
                for output in relative.outputs:
                    if (level, output.name) not in relative._box_epilogues:
                        getattr(self.runtime, 'box%s_%s_epilogue' % (
                            suffix, output.name))(output, relative)
                        relative._box_epilogues.add((level, output.name))
                if level not in relative._box_epilogues:
                    getattr(self.runtime, 'box%s_epilogue' % (
                        suffix))(relative)
                    relative._box_epilogues.add(level)
            for child in self.boxes:
                child.box(stage='epilogues')

    def link(self):
        """
        Link together import/exports from boxes.
        """
        # first deduplicate exports and imports (may have been created
        # during boxing)
        importset = {}
        for import_ in self.imports:
            if (import_.scope, import_.name) in importset:
                conflict = importset[(import_.scope, import_.name)]
                assert conflict.iscompatible(import_), (
                    "Incompatible imports for `%s`:\n%s" % (
                        import_.name,
                        '\n'.join(x.reprcontext() for x in
                            it.chain([conflict, import_]))))
            # prioritize our own imports
            if ((import_.scope, import_.name) not in importset
                    or import_.source == self.name):
                importset[(import_.scope, import_.name)] = import_
        # actually don't make this unique, 
        self.imports = sorted(self.imports)

        exportset = {}
        for export in self.exports:
            if (export.scope, export.name) in exportset:
                conflict = exportset[(export.scope, export.name)]
                assert export.weak or conflict.weak, (
                    "Conflicting exports for `%s`:\n%s" % (
                        export.name,
                        '\n'.join(x.reprcontext() for x in
                            it.chain([conflict, export]))))
                assert conflict.iscompatible(export), (
                    "Incompatible exports for `%s`:\n%s" % (
                        export.name,
                        '\n'.join(x.reprcontext() for x in
                            it.chain([conflict, export]))))
            if (export.scope, export.name) not in exportset or conflict.weak:
                exportset[(export.scope, export.name)] = export
        self.exports = sorted(exportset.values())

        # now create linkages
        for export in self.exports:
            assert (export.scope is None or any(
                scope.name == export.scope
                for scope in it.chain(
                    [self],
                    [self.parent] if self.parent else [],
                    self.boxes))), (
                "No scope `%s` found for export `%s`:\n%s" % (
                    export.scope,
                    export.name,
                    export.reprcontext()))

        for import_ in self.imports:
            targets = []
            for scope in it.chain(
                    [self],
                    [self.parent] if self.parent else [],
                    self.boxes):
                for export in scope.exports:
                    if import_.islinkable(export, scope, self):
                        targets.append(export)

            assert targets or import_.weak, (
                "No export found for `%s`:\n%s" % (
                    import_.name,
                    import_.reprcontext()))

            # remove weaks
            while len(targets) > 1 and any(scope.weak for scope in targets):
                maxweak = max(scope.weak for scope in targets)
                targets = [scope for scope in targets
                    if scope.weak < maxweak]
            assert len(targets) <= 1, (
                "Ambiguous import/export for `%s`:\n%s" % (
                    import_.name,
                    '\n'.join(x.reprcontext() for x in
                        it.chain([import_], targets))))

            if targets:
                export = targets[0]
                assert export.iscompatible(import_), (
                    "Incompatible import/export for `%s`:\n%s" % (
                        export.name,
                        '\n'.join(x.reprcontext() for x in
                            [export, import_])))

                link = Link(export, import_)
                import_.link = link
                export.links.append(link)

        # link children
        for child in self.boxes:
            child.link()

        # create "n" functions. these generate compact unique numbers
        # for boxes/links/whatever
        for export in self.exports:
            def n(self):
                def n(box=None):
                    for n, export in enumerate(
                            export for export in self.box.exports
                            if not box or any(
                                link.import_.box == box
                                for link in export.links)
                            if export.scope != export.box):
                        if export is self:
                            return n
                return n
            export.box = self
            export.n = n(export)

        for import_ in self.imports:
            def n(self):
                def n(box=None):
                    for n, import_ in enumerate(
                            import_ for import_ in self.box.imports
                            if not box or import_.link.export.box == box
                            if import_.link.export.scope !=
                                import_.link.export.box):
                        if import_ is self:
                            return n
                return n
            import_.box = self
            import_.n = n(import_)

        for child in self.boxes:
            def n(self):
                def n(runtime=None):
                    if not self.parent:
                        return 0
                    for n, box in enumerate(
                            box for box in self.parent.boxes
                            if not runtime or box.runtime == runtime):
                        if box is self:
                            return n
                return n
            child.n = n(child)

    def build(self, stage=None):
        """
        Generate output data based on configured runtimes and outputs.
        """
        if not stage or stage == 'prologues':
            self._build_prologues = set()
            for level, suffix, relative in [
                    ('root', '_root', self.getroot()),
                    ('muxer', '_muxer', self.getmuxer()),
                    ('parent', '_parent', self.getparent()),
                    ('box', '', self)]:
                if not relative:
                    continue
                for output in relative.outputs:
                    if (level, output.name) not in relative._build_prologues:
                        with output.pushattrs(**{level: relative.name}):
                            getattr(self.runtime, 'build%s_%s_prologue' % (
                                suffix, output.name))(output, relative)
                        relative._build_prologues.add((level, output.name))
                if level not in relative._build_prologues:
                    getattr(self.runtime, 'build%s_prologue' % (
                        suffix))(relative)
                    relative._build_prologues.add(level)
            for child in self.boxes:
                child.build(stage='prologues')

        if not stage or stage == 'runtimes':
            for level, suffix, relative, *args in [
                    ('root', '_root', self.getroot(), self),
                    ('muxer', '_muxer', self.getmuxer(), self),
                    ('parent', '_parent', self.getparent(), self),
                    ('box', '', self)]:
                if not relative:
                    continue
                for output in relative.outputs:
                    with output.pushattrs(**{
                            'box': args[0].name if args else None,
                            level: relative.name}):
                        getattr(self.runtime, 'build%s_%s' % (
                            suffix, output.name))(output, relative, *args)
                getattr(self.runtime, 'build%s' % (
                    suffix))(relative, *args)
            for child in self.boxes:
                child.build(stage='runtimes')

        if not stage or stage == 'epilogues':
            self._build_epilogues = set()
            for level, suffix, relative in [
                    ('root', '_root', self.getroot()),
                    ('muxer', '_muxer', self.getmuxer()),
                    ('parent', '_parent', self.getparent()),
                    ('box', '', self)]:
                if not relative:
                    continue
                for output in relative.outputs:
                    if (level, output.name) not in relative._build_epilogues:
                        with output.pushattrs(**{level: relative.name}):
                            getattr(self.runtime, 'build%s_%s_epilogue' % (
                                suffix, output.name))(output, relative)
                        relative._build_epilogues.add((level, output.name))
                if level not in relative._build_epilogues:
                    getattr(self.runtime, 'build%s_epilogue' % (
                        suffix))(relative)
                    relative._build_epilogues.add(level)
            for child in self.boxes:
                child.build(stage='epilogues')
