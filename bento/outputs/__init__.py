import os
import builtins
import abc
import collections as co
import itertools as it
import string
import io
import re

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
        self._attrs.append(kwargs)

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
                if isinstance(v, str) and re.search(r'%(?!%)', v):
                    return v % self.attrs()
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

    def __repr__(self):
        return super(object, self).__repr__()


class OutputField(list):
    def __init__(self, parent=None, rules={}, **kwargs):
        super().__init__()
        self._parent = parent
        self._rules = rules
        self._attrs = kwargs

    def insert(self, _i, _fmt=None, **kwargs):
        if isinstance(_fmt, OutputBlob):
            outf = _fmt
        else:
            outf = OutputBlob(**{
                **self._parent.attrs(),
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

    def __repr__(self):
        return super(object, self).__repr__()

class Output(OutputBlob):
    """An optional output that a runtime can generate."""
    __argname__ = "unnamed_output"
    __arghelp__ = __doc__

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

    def __lt__(self, other):
        return self.name < other.name

    def box(self, box):
        self.pushattrs(
            name=self.name,
            path=self.path,
            box=box.name if box.isbox() else None)

    def build(self, box):
        pass

# Output class imports
# These must be imported here, since they depend on the above utilities
from .h import HOutput
from .c import COutput
from .ld import LDOutput, PartialLDOutput
