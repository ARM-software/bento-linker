import os
import builtins
import collections as co
import itertools as it
import string
from .. import outputs

RUNTIMES = co.OrderedDict()
def runtime(cls):
    assert cls.__argname__ not in RUNTIMES
    RUNTIMES[cls.__argname__] = cls
    return cls

class Runtime(outputs.OutputBlob):
    """A bento-box runtime."""
    __argname__ = "runtime"
    __arghelp__ = __doc__

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

    def box_box(self, box):
        box.text.memory     = box.consume('rx', section=box.text)
        box.stack.memory    = box.consume('rw', section=box.stack)
        box.data.memory     = box.consume('rw', section=box.data)
        box.bss.memory      = box.consume('rw', section=box.bss)
        box.heap.memory     = box.consume('rw', section=box.heap)

    def box(self, box):
        for level, lbox in [
                ('root', box.getroot()),
                ('muxer', box.getmuxer()),
                ('parent', box.getparent()),
                ('box', box)]:
            if not lbox:
                continue

            if ('runtime', level) not in lbox.box_prologues:
                def prologue(f, lbox):
                    def prologue():
                        f(lbox)
                    return prologue
                lbox.box_prologues[('runtime', level)] = prologue(
                    getattr(self, 'box_%s_prologue' % level),
                    lbox)
                lbox.box_prologues[('runtime', level)]()

            if level != 'box':
                getattr(self, 'box_%s' % level)(lbox, box)
            else:
                getattr(self, 'box_%s' % level)(box)

            if ('runtime', level) not in lbox.box_epilogues:
                def epilogue(f, lbox):
                    def epilogue():
                        f(lbox)
                    return epilogue
                lbox.box_epilogues[('runtime', level)] = epilogue(
                    getattr(self, 'box_%s_epilogue' % level),
                    lbox)

    def link(self, box):
        for level, lbox in [
                ('root', box.getroot()),
                ('muxer', box.getmuxer()),
                ('parent', box.getparent()),
                ('box', box)]:
            if not lbox:
                continue

            if ('runtime', level) not in lbox.link_prologues:
                def prologue(f, lbox):
                    def prologue():
                        f(lbox)
                    return prologue
                lbox.link_prologues[('runtime', level)] = prologue(
                    getattr(self, 'link_%s_prologue' % level),
                    lbox)
                lbox.link_prologues[('runtime', level)]()

            if level != 'box':
                getattr(self, 'link_%s' % level)(lbox, box)
            else:
                getattr(self, 'link_%s' % level)(box)

            if ('runtime', level) not in lbox.link_epilogues:
                def epilogue(f, lbox):
                    def epilogue():
                        f(lbox)
                    return epilogue
                lbox.link_epilogues[('runtime', level)] = epilogue(
                    getattr(self, 'link_%s_epilogue' % level),
                    lbox)

    def build(self, box):
        attrs = self.attrs()
        for level, lbox in [
                ('root', box.getroot()),
                ('muxer', box.getmuxer()),
                ('parent', box.getparent()),
                ('box', box)]:
            if not lbox:
                continue

            for output in lbox.outputs:
                if ('runtime', level, output.name) not in lbox.build_prologues:
                    def prologue(f, output, lbox):
                        def prologue():
                            with output.pushattrs(**{**attrs,
                                    level: lbox.name}):
                                f(output, lbox)
                        return prologue
                    lbox.build_prologues[('runtime', level, output.name)] = (
                        prologue(getattr(self, 'build_%s_%s_prologue'
                            % (level, output.name)), output, lbox))
                    lbox.build_prologues[('runtime', level, output.name)]()

                if level != 'box':
                    with output.pushattrs(**{**attrs,
                            level: lbox.name, 'box': box.name}):
                        getattr(self, 'build_%s_%s' % (level, output.name))(
                            output, lbox, box)
                else:
                    with output.pushattrs(**{**attrs, 'box': box.name}):
                        getattr(self, 'build_%s_%s' % (level, output.name))(
                            output, box)

                if ('runtime', level, output.name) not in lbox.build_epilogues:
                    def epilogue(f, output, lbox):
                        def epilogue():
                            with output.pushattrs(**{**attrs,
                                    level: lbox.name}):
                                f(output, lbox)
                        return epilogue
                    lbox.build_epilogues[('runtime', level, output.name)] = (
                        epilogue(getattr(self, 'build_%s_%s_epilogue'
                            % (level, output.name)), output, lbox))


# if box rule doesn't exist, fall back to noop
for level, order in it.product(
        ['root', 'muxer', 'parent', 'box'],
        ['_prologue', '', '_epilogue']):
    method = 'box_%s%s' % (level, order)
    if not hasattr(Runtime, method):
        setattr(Runtime, method,
            lambda self, *args, **kwargs: None)

for level, order in it.product(
        ['root', 'muxer', 'parent', 'box'],
        ['_prologue', '', '_epilogue']):
    method = 'link_%s%s' % (level, order)
    if not hasattr(Runtime, method):
        setattr(Runtime, method,
            lambda self, *args, **kwargs: None)

# if build rule doesn't exist, fall back to output defaults, or noop
from ..outputs import OUTPUTS
for Output in OUTPUTS.values():
    for level, order in it.product(
            ['root', 'muxer', 'parent', 'box'],
            ['_prologue', '', '_epilogue']):
        default = 'default_build_%s%s' % (level, order)
        method  = 'build_%s_%s%s' % (level, Output.__argname__, order)
        if not hasattr(Runtime, method):
            if hasattr(Output, default):
                setattr(Runtime, method, (lambda f:
                    lambda self, output, *args, **kwargs:
                        f(output, *args, **kwargs)
                    )(getattr(Output, default)))
            else:
                setattr(Runtime, method,
                    lambda self, output, *args, **kwargs: None)

# Runtime class imports
# These must be imported here, since they depend on the above utilities
from .system import SystemRuntime
from .noop import NoOpRuntime
from .wasm3 import Wasm3Runtime
from .armv7m_sys import ARMv7MSysRuntime
from .armv7m_mpu import ARMv7MMPURuntime
from .armv8m_mpu import ARMv8MMPURuntime
