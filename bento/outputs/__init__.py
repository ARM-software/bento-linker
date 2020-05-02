import os
import builtins
import abc
import collections as c
import itertools as it
import string
import io

OUTPUTS = {'box': c.OrderedDict(), 'sys': c.OrderedDict()}
def output(target):
    def output(cls):
        assert cls.__argname__ not in OUTPUTS[target]
        OUTPUTS[target][cls.__argname__] = cls
        return cls
    return output

class Output_(io.StringIO):
    def __init__(self, *args, **kwargs):
        self._attrs = [kwargs]
        super().__init__(*args)

    def write(self, fmt, **kwargs):
        fmt = '\n'.join(self.get('indent', 0)*' ' + line
            for line in fmt.splitlines())
        super().write(fmt % self.attrs(**kwargs))

    def build(self, outf):
        outf.write(super().getvalue())

    def getvalue(self):
        # reimplemented to allow subclasses to only override build
        outf = io.StringIO()
        self.build(outf)
        return outf.getvalue()

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

    def pushindent(self, indent=4):
        return self.pushattrs(indent=self.get('indent', 0) + indent)

    def popindent(self):
        assert set(self._attrs[-1].keys()) == {'indent'}
        return self.popattrs()['indent']

    def __getitem__(self, key):
        for a in reversed(self._attrs):
            if key in a:
                return a[key]
        else:
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
        return attrs

    def __repr__(self):
        return super(object, self).__repr__()

class OutputField_(list):
    def __init__(self, parent=None, iter=[]):
        self._parent = parent
        super().__init__(iter)

    def insert(self, i, fmt=None, **kwargs):
        attrs = self._parent.getattrs(**kwargs)
        out = Output_(**attrs)
        if fmt is not None:
            out.write(fmt)
        super().insert(i, out)
        return out

    def append(self, fmt=None, **kwargs):
        out = Output_(**self._parent.attrs(**kwargs))
        if fmt is not None:
            out.write(fmt)
        super().append(out)
        return out

    def __repr__(self):
        return super(object, self).__repr__()

class Output(abc.ABC):
    """An optional output that a runtime can generate."""
    __argname__ = "output"
    __arghelp__ = __doc__

    def __init__(self, sys, box, path):
        self.path = path
        # some common spec entries
        f = {'path': path}
        if box is not None:
            f.update({'box': box.name, 'BOX': box.name.upper()})
        self._format = [f]
        super().__init__()

    def format(self, **kwargs):
        self._format[-1].update(kwargs)

    def mkformat(self, **kwargs):
        format = {}
        for f in self._format:
            format.update(f)
        format.update(kwargs)
        return format

    def mkfield(self, **kwargs):
        return OutputField(**self.mkformat(**kwargs))

    def pushformat(self, **kwargs):
        self._format.append(kwargs)

    def popformat(self):
        return self._format.pop()

    @abc.abstractmethod
    def build(self, outf):
        """Build the output after being passed to the needed runtimes."""

class OutputField(io.StringIO):
    def __init__(self, *args, **kwargs):
        self._format = kwargs
        super().__init__(*args)

    def write(self, fmt, **kwargs):
        super().write(fmt % {**kwargs, **self._format})

# Output class imports
# These must be imported here, since they depend on the above utilities
from .header import HeaderOutput, HeaderGlueOutput_
from .jumptable import JumptableOutput
from .linkerscript import LinkerScriptOutput
