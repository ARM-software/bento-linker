
from .. import runtimes

@runtimes.runtime
class SystemRuntime(runtimes.Runtime):
    """
    The root runtime of a device.
    """
    __argname__ = "system"
    __arghelp__ = __doc__
    def __init__(self):
        super().__init__()
