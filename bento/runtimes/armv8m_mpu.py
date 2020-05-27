from .. import argstuff
from .. import runtimes
import math
import itertools as it
from .armv7m_mpu import ARMv7MMPURuntime

BOX_STRUCT_MPUREGIONS = """
struct __box_mpuregions {
    uint32_t count;
    uint32_t regions[][2];
};
"""

BOX_MPU_DISPATCH = """
#define SHCSR        ((volatile uint32_t*)0xe000ed24)
#define MPU_TYPE     ((volatile uint32_t*)0xe000ed90)
#define MPU_CTRL     ((volatile uint32_t*)0xe000ed94)
#define MPU_MAIR0    ((volatile uint32_t*)0xe000edc0)
#define MPU_MAIR1    ((volatile uint32_t*)0xe000edc4)
#define MPU_RNR      ((volatile uint32_t*)0xe000ed98)
#define MPU_RBAR     ((volatile uint32_t*)0xe000ed9c)
#define MPU_RLAR     ((volatile uint32_t*)0xe000eda0)

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
        *MPU_RBAR = %(callprefix)#010x | 0x1;
        *MPU_RLAR = (~0x1f & (
            %(callprefix)#010x + %(callregionsize)#010x-1))
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

    def box_parent(self, parent, box):
        assert math.log2(self._call_region.size) % 1 == 0, (
            "MPU call region is not aligned to a power-of-two %s"
                % self._call_region)
        assert self._call_region.addr % self._call_region.size == 0, (
            "MPU call region is not aligned to size %s"
                % self._call_region)
        self.pushattrs(
            callprefix=self._call_region.addr,
            callmask=(self._call_region.size//2)-1,
            retprefix=self._call_region.addr + self._call_region.size//2,
            retmask=(self._call_region.size//2)-1,
            callregionaddr=self._call_region.addr,
            callregionsize=self._call_region.size,
            callregionlog2=int(math.log2(self._call_region.size)),
            mpuregions=self._mpu_regions)

        for box in parent.boxes:
            if box.runtime == self:
                for memory in box.memories:
                    assert memory.size >= 32, (
                        "Memory region %s too small (< 32 bytes)"
                            % memory.name)
                    assert memory.addr % 32 == 0 and memory.size % 32 == 0, (
                        "Memory region %s not aligned to 32 byte address"
                            % memory.name)

        self.ids = {}

        for j, export in enumerate(it.chain(
                ['__box_write'],
                (export.name for export in parent.exports))):
            self.ids[export] = j*(len(parent.boxes)+1)

        for i, box in enumerate(parent.boxes):
            # TODO make unique name?
            self.ids['box ' + box.name] = i+1
            for j, export in enumerate(it.chain(
                    ['__box_%s_rawinit' % box.name],
                    (export.name for export in box.exports))):
                self.ids[export] = j*(len(parent.boxes)+1) + i+1

    def build_mpu_dispatch(self, output, sys):
        output.decls.append(BOX_STRUCT_MPUREGIONS)
        output.decls.append(BOX_MPU_DISPATCH)

    def build_mpu_regions(self, output, sys, box):
        out = output.decls.append(box=box.name)
        out.printf('const struct __box_mpuregions '
            '__box_%(box)s_mpuregions = {')
        with out.pushindent():
            out.printf('.count = %(count)d,',
                count=len(box.memories))
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



