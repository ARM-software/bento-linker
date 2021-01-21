#
# Runtime for the ARMv8 base system
# 
# Copyright (c) 2020, Arm Limited. All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause
#

from .. import argstuff
from .. import runtimes
from ..glue import override
from .armv7m_sys import ARMv7MSysRuntime

@runtimes.runtime
class ARMv8MSysRuntime(ARMv7MSysRuntime):
    """
    A bento-box runtime that runs in privledge mode on the system.
    Usually required at the root of the project.
    """
    __argname__ = "armv8m_sys"
    __arghelp__ = __doc__

    @override(ARMv7MSysRuntime)
    def _box_esr_hooks(self, box):
        return [
            box.addimport('__box_nmi_handler', 'fn() -> void',
                scope=box.name, source=self.__argname__, weak=True),
            box.addimport('__box_hardfault_handler', 'fn() -> void',
                scope=box.name, source=self.__argname__, weak=True),
            box.addimport('__box_memmanage_handler', 'fn() -> void',
                scope=box.name, source=self.__argname__, weak=True),
            box.addimport('__box_busfault_handler', 'fn() -> void',
                scope=box.name, source=self.__argname__, weak=True),
            box.addimport('__box_usagefault_handler', 'fn() -> void',
                scope=box.name, source=self.__argname__, weak=True),
            box.addimport('__box_securefault_handler', 'fn() -> void',
                scope=box.name, source=self.__argname__, weak=True),
            None,
            None,
            None,
            box.addimport('__box_svc_handler', 'fn() -> void',
                scope=box.name, source=self.__argname__, weak=True),
            box.addimport('__box_debugmon_handler', 'fn() -> void',
                scope=box.name, source=self.__argname__, weak=True),
            None,
            box.addimport('__box_pendsv_handler', 'fn() -> void',
                scope=box.name, source=self.__argname__, weak=True),
            box.addimport('__box_systick_handler', 'fn() -> void',
                scope=box.name, source=self.__argname__, weak=True),
        ]
