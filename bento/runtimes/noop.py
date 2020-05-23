
from .. import runtimes

@runtimes.runtime
class NoOpRuntime(runtimes.Runtime):
    """
    A runtime that adds no restrictions to a bento-box.
    """
    __argname__ = "noop"
    __arghelp__ = __doc__
    def __init__(self):
        print("hi I'm noop")
