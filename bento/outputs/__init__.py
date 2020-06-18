import os
import builtins
import abc
import collections as co
import itertools as it
import string
import io
import re
from ..glue import Inherit

OUTPUTS = co.OrderedDict()
def output(cls):
    assert cls.__argname__ not in OUTPUTS
    OUTPUTS[cls.__argname__] = cls
    return cls

# TODO enable inclusive inheritance between StringIO and file?
class OutputBlob(io.StringIO):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self._attrs = []
        self._needindent = True
        self.pushattrs(**{'':''})
        self.pushattrs(**kwargs)

    def writef(self, _fmt, **kwargs):
        _fmt = _fmt % self.attrs(**kwargs)
        for c in _fmt:
            if c == '\n':
                self._needindent = True
            else:
                if self._needindent:
                    self._needindent = False
                    super().write(self.get('indent', 0)*' ')
            self.write(c)

    def print(self, *args):
        for arg in args:
            self.write(str(arg))
        self.write('\n')

    def printf(self, *args, **kwargs):
        for arg in args:
            self.writef(str(arg), **kwargs)
        self.writef('\n')

    def pushattrs(self, **kwargs):
        nkwargs = {}
        for k, v in kwargs.items():
            while isinstance(v, str) and '%(' in v:
                v = v % self.attrs(**kwargs)
            nkwargs[k] = v

        self._attrs.append(nkwargs)

        class context:
            def __enter__(_):
                return self
            def __exit__(*_):
                self.popattrs()
        return context()

    def popattrs(self):
        return self._attrs.pop()

    def indent(self, indent=4):
        """ alias for pushindent """
        return self.pushindent()

    def pushindent(self, indent=4):
        return self.pushattrs(indent=self.get('indent', 0) + indent)

    def popindent(self):
        assert set(self._attrs[-1].keys()) == {'indent'}
        return self.popattrs()['indent']

    def _expand(self, k, v):
        with self.pushattrs(**{k: None}):
            for rule in [lambda: v(self), lambda: v()]:
                try:
                    return rule()
                except TypeError:
                    continue
            else:
                return v

    def _expandall(self, attrs):
        expanded = {}
        for k, v in attrs.items():
            if v is None:
                continue
            expanded[k] = self._expand(k, v)
            if k.upper() not in expanded and isinstance(expanded[k], str):
                expanded[k.upper()] = expanded[k].upper()
        return expanded

    def __getitem__(self, key):
        for a in reversed(self._attrs):
            if key in a:
                return self._expand(key, a[key])

        for a in reversed(self._attrs):
            a = {k.upper(): v for k, v in a.items()}
            if key in a:
                return self._expand(key, a[key]).upper()

        raise KeyError(key)

    def __contains__(self, key):
        try:
            self[key]
            return True
        except KeyError:
            return False

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def attrs(self, **kwargs):
        attrs = {}
        for a in self._attrs:
            attrs.update(a)
        attrs.update(kwargs)
        return self._expandall(attrs)

    def __str__(self):
        return self.getvalue()

class OutputField(list):
    def __init__(self, inherit=None, rules={}, **kwargs):
        super().__init__()
        self._inherit = inherit
        self._rules = rules
        self._attrs = kwargs

    def insert(self, _i, _fmt=None, **kwargs):
        if isinstance(_fmt, OutputBlob):
            outf = _fmt
        else:
            outf = OutputBlob(**{
                **self._inherit.attrs(),
                **self._attrs,
                **kwargs})

            for type, rule in self._rules.items():
                if isinstance(_fmt, type):
                    rule(outf, _fmt)
                    break
            else:
                if _fmt is not None:
                    outf.writef(_fmt)

        super().insert(_i, outf)
        return outf

    def append(self, _fmt=None, **kwargs):
        return self.insert(len(self), _fmt, **kwargs)

    def extend(self, iterable):
        for x in iterable:
            self.append(x)

class Output(Inherit(
        ['%s%s%s' % (op, level, order)
        for op, level, order in it.product(
            ['box', 'build'],
            ['_root', '_muxer', '_parent', ''],
            ['_prologue', '', '_epilogue'])]), OutputBlob):
    @classmethod
    def __argparse__(cls, parser, **kwargs):
        parser.add_argument("path",
            help=cls.__arghelp__)
        parser.add_argument("--path",
            help=cls.__arghelp__)

    def __init__(self, path=None):
        super().__init__()
        self.name = self.__argname__
        self.path = path

    def __eq__(self, other):
        if isinstance(other, Output):
            return self.name == other.name
        else:
            return self.name == other

    def __lt__(self, other):
        if isinstance(other, Output):
            return self.name < other.name
        else:
            return self.name < other

    def box(self, box):
        super().box(box)
        self.pushattrs(
            name=self.name,
            path=self.path,
            root=getattr(box.getroot(), 'name', None),
            muxer=getattr(box.getmuxer(), 'name', None),
            parent=getattr(box.getparent(), 'name', None),
            box=box.name)

# Output class imports
# These must be imported here, since they depend on the above utilities
from .h import HOutput
from .c import COutput
from .ld import LDOutput
from .mk import MKOutput

# output glue for connecting default runtime generation
import importlib
from .. import glue
importlib.reload(glue)

class OutputGlue(glue.Glue):
    __argname__ = "output_glue"
    def __init__(self):
        # we offer redirection for build_parent_mk -> parent.mk.build_parent
        for op, level, Output, order in it.product(
                ['box', 'build'],
                ['_root', '_muxer', '_parent', ''],
                OUTPUTS.values(),
                ['_prologue', '', '_epilogue']):
            m = getattr(Output, '%s%s%s' % (op, level, order), None)
            if m:
                setattr(self, '%s%s_%s%s' % (
                    op, level, Output.__argname__, order), m)

