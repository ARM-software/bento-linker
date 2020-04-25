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
from .header import HeaderOutput
from .jumptable import JumptableOutput
from .linkerscript import LinkerScriptOutput
