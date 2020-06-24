import collections as co
import itertools as it
from ..glue import Inherit

LOADERS = co.OrderedDict()
def loader(cls):
    assert cls.__argname__ not in LOADERS
    LOADERS[cls.__argname__] = cls
    return cls

from ..outputs import OUTPUTS
class Loader(Inherit(
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

    def constraints(self, constraints):
        """
        Allow loaders to override memory constraints requested
        during memory allocations.
        """
        return constraints

    def box(self, box):
        super().box(box)
        box.text    .alloc(box, 'rxp')
        box.stack   .alloc(box, 'rw')
        box.data    .alloc(box, 'rw')
        box.bss     .alloc(box, 'rw')
        box.heap    .alloc(box, 'rw')

# Runtime class imports
# These must be imported here, since they depend on the above utilities
from .noop import NoOpLoader
from .glz import GLZLoader
