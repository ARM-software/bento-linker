#
# Runtime for the ARMv8 MPU
# 
# Copyright (c) 2020, Arm Limited. All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause
#

from .. import argstuff
from .. import runtimes
from ..box import Region
from ..glue import override
from .armv7m_mpu import ARMv7MMPURuntime
import itertools as it

MPU_IMPL = """
#define SHCSR        ((volatile uint32_t*)0xe000ed24)
#define MPU_TYPE     ((volatile uint32_t*)0xe000ed90)
#define MPU_CTRL     ((volatile uint32_t*)0xe000ed94)
#define MPU_MAIR0    ((volatile uint32_t*)0xe000edc0)
#define MPU_MAIR1    ((volatile uint32_t*)0xe000edc4)
#define MPU_RNR      ((volatile uint32_t*)0xe000ed98)
#define MPU_RBAR     ((volatile uint32_t*)0xe000ed9c)
#define MPU_RLAR     ((volatile uint32_t*)0xe000eda0)

struct __box_mpuregions {
    uint32_t control;
    uint32_t count;
    uint32_t regions[][2];
};

static int32_t __box_mpu_init(void) {
    // make sure MPU is initialized
    if (!(*MPU_CTRL & 0x1)) {
        // do we have an MPU?
        assert(*MPU_TYPE >= %(mpuregions)d);
        // enable MemManage exception
        *SHCSR = *SHCSR | 0x00070000;
        // setup call region, dissallow execution
        *MPU_RNR = 0;
        *MPU_MAIR0 = 0x00000044;
        *MPU_RBAR = (uint32_t)&__box_callregion | 0x1;
        *MPU_RLAR = (~0x1f & (
            (uint32_t)&__box_callregion + %(callsize)d - 1))
            | 0x1;
        // enable the MPU
        *MPU_CTRL = 5;
    }
    return 0;
}

static void __box_mpu_switch(const struct __box_mpuregions *regions) {
    *MPU_CTRL = 0;
    uint32_t count = regions->count;
    for (int i = 0; i < %(mpuregions)d; i++) {
        if (i < count) {
            *MPU_RNR = i+1;
            *MPU_RBAR = regions->regions[i][0];
            *MPU_RLAR = regions->regions[i][1];
        } else {
            *MPU_RNR = i+1;
            *MPU_RBAR = 0;
            *MPU_RLAR = 0;
        }
    }
    *MPU_CTRL = 5;

    // update CONTROL state, note that return-from-exception acts
    // as an instruction barrier
    uint32_t control;
    __asm__ volatile ("mrs %%0, control" : "=r"(control));
    control = (~1 & control) | (regions->control);
    __asm__ volatile ("msr control, %%0" :: "r"(control));
}
"""

@runtimes.runtime
class ARMv8MMPURuntime(ARMv7MMPURuntime):
    """
    A bento-box runtime that uses a v8 MPU to provide memory isolation
    between boxes.
    """
    __argname__ = "armv8m_mpu"
    __arghelp__ = __doc__

    @override(ARMv7MMPURuntime)
    def _box_call_region(self, parent):
        callmemory = parent.bestmemory(
            'rx', size=0, reverse=True).origmemory
        addr = callmemory.addr + callmemory.size

        importcount = max(it.chain(
            [3+sum(len(box.exports)
                for box in parent.boxes
                if box.runtime == self)],
            (4+len(box.imports)
                for box in parent.boxes
                if box.runtime == self)))
        # fit into MPU limits
        size = (((4*importcount)+31)//32)*32

        return Region(addr=addr, size=size)

    @override(ARMv7MMPURuntime)
    def _check_call_region(self, call_region):
        assert call_region.addr % 32 == 0 and call_region.size % 32 == 0, (
            "%s: MPU call region not aligned to 32 byte address"
                % (self.name, call_region))
        assert call_region.size >= 32, (
            "%s: MPU call region too small (< 32 bytes) `%r`"
                % (self.name, call_region))

    @override(ARMv7MMPURuntime)
    def _check_mpu_region(self, memory):
        assert memory.addr % 32 == 0 and memory.size % 32 == 0, (
            "%s: Memory region `%s` not aligned to 32 byte address"
                % (self.name, memory.name, memory))
        assert memory.size >= 32, (
            "%s: Memory region `%s` too small (< 32 bytes) `%r`"
                % (self.name, memory.name, memory))

    @override(ARMv7MMPURuntime)
    def _build_mpu_impl(self, output, parent):
        output.decls.append(MPU_IMPL)

    @override(ARMv7MMPURuntime)
    def _build_mpu_sysregions(self, output, parent):
        out = output.decls.append()
        out.printf('const struct __box_mpuregions __box_sys_mpuregions = {')
        with out.pushindent():
            out.printf('.control = 0,')
            out.printf('.count = 0,')
            out.printf('.regions = {}')
        out.printf('};')

    @override(ARMv7MMPURuntime)
    def _build_mpu_regions(self, output, parent, box):
        out = output.decls.append(box=box.name)
        out.printf('const struct __box_mpuregions __box_%(box)s_mpuregions = {')
        with out.pushindent():
            out.printf('.control = 1,')
            out.printf('.count = %(count)d,', count=len(box.memories))
            out.printf('.regions = {')
            with out.pushindent():
                for memory in box.memories:
                    out.printf('{%(rbar)#010x, %(rlar)#010x},',
                        rbar=memory.addr
                            | (0x1 if 'x' not in memory.mode else 0x0)
                            | (0x2
                                if set('rw').issubset(memory.mode) else
                                0x6
                                if 'r' in memory.mode else
                                0x4),
                        rlar=(~0x1f & (memory.addr+memory.size-1))
                            | 0x1)
            out.printf('},')
        out.printf('};')

