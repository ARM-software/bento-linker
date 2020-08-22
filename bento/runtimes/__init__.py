import builtins
import collections as co
import itertools as it
from ..glue import Inherit

RUNTIMES = co.OrderedDict()
def runtime(cls):
    assert cls.__argname__ not in RUNTIMES
    RUNTIMES[cls.__argname__] = cls
    return cls

from ..outputs import OUTPUTS
class Runtime(Inherit(
        ['%s%s%s%s' % (op, level, output, order)
        for op, level, output, order in it.product(
            ['box', 'build'],
            ['_root', '_muxer', '_parent', ''],
            ['_'+Output.__argname__ for Output in OUTPUTS.values()] + [''],
            ['_prologue', '', '_epilogue'])])):
    def __init__(self):
        super().__init__()
        self.name = self.__argname__

    def __eq__(self, other):
        if isinstance(other, Runtime):
            return self.name == other.name
        else:
            return self.name == other

    def __lt__(self, other):
        if isinstance(other, Runtime):
            return self.name < other.name
        else:
            return self.name < other

    def box(self, box):
        super().box(box)
        self.data_init_hook = box.addimport(
            '__box_data_init', 'fn() -> void',
            scope=box.name, source=self.__argname__, weak=True,
            doc="Artificial hook to indicate who's taking care of "
                "initializing the data section. Some loaders take care of "
                "initialization implicitly, otherwise its left up to the "
                "runtime. Not actually called.")
        self.bss_init_hook = box.addimport(
            '__box_bss_init', 'fn() -> void',
            scope=box.name, source=self.__argname__, weak=True,
            doc="Artificial hook to indicate who's taking care of "
                "initializing the bss section. Some loaders take care of "
                "initialization implicitly, otherwise its left up to the "
                "runtime. Not actually called.")


# Runtime class imports
# These must be imported here, since they depend on the above utilities
from .system import SystemRuntime
from .jumptable import JumptableRuntime
from .noop import NoOpRuntime
from .armv7m_sys import ARMv7MSysRuntime
from .armv8m_sys import ARMv8MSysRuntime
from .armv7m_mpu import ARMv7MMPURuntime
from .armv8m_mpu import ARMv8MMPURuntime
from .awsm import aWsmRuntime
from .wasm3 import Wasm3Runtime
