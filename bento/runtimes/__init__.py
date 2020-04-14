import os
import builtins
import abc
import collections as c
import itertools as it
import string

RUNTIMES = c.OrderedDict()
def runtime(cls):
    assert cls.__argname__ not in RUNTIMES
    RUNTIMES[cls.__argname__] = cls
    return cls

class Runtime(abc.ABC):
    """A bento-box runtime."""
    __argname__ = "runtime"
    __arghelp__ = __doc__

# Runtime class imports
# These must be imported here, since they depend on the above utilities
from .mpu_protect import MPUProtectRuntime
from .noop import NoOpRuntime
from .wasm3 import Wasm3Runtime
