import os
import builtins
import abc
import collections as c
import itertools as it
import string

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

    @abc.abstractmethod
    def build(self, sys, box, outf):
        """Build the output after being passed to the needed runtimes."""

# Output class imports
# These must be imported here, since they depend on the above utilities
from .header import HeaderOutput
from .jumptable import JumptableOutput
from .linkerscript import LinkerScriptOutput
