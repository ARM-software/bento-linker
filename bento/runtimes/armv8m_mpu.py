from .. import argstuff
from .. import runtimes
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

//
//#define SHCSR    ((volatile uint32_t*)0xe000ed24)
//#define MPU_TYPE ((volatile uint32_t*)0xe000ed90)
//#define MPU_CTRL ((volatile uint32_t*)0xe000ed94)
//#define MPU_RBAR ((volatile uint32_t*)0xe000ed9c)
//#define MPU_RASR ((volatile uint32_t*)0xe000eda0)

static int32_t __box_mpu_init(void) {
    // make sure MPU is initialized
    if (!(*MPU_CTRL & 0x1)) {
        // do we have an MPU?
        assert(*MPU_TYPE >= %(mpuregions)d);
        // enable MemManage exception
        *SHCSR = *SHCSR | 0x00030000;
        // setup call region, dissallow execution
        *MPU_RNR = 1;
        //*MPU_MAIR0 = 0x00000044;
        *MPU_RBAR = %(callprefix)#010x | 0x5; //0x1; //0x5;
        *MPU_RLAR = (~0x1f & (
            %(callprefix)#010x + %(callregionsize)#010x-1))
            | 0x1;
        // enable the MPU
        *MPU_CTRL = 5;
//        printf("set SHCSR    0x%%08x\\n", *SHCSR);
//        printf("set MPU_RNR  0x%%08x\\n", *MPU_RNR);
//        printf("set MPU_RBAR 0x%%08x\\n", *MPU_RBAR);
//        printf("set MPU_RLAR 0x%%08x\\n", *MPU_RLAR);
//        printf("set MPU_CTRL 0x%%08x\\n", *MPU_CTRL);
//        __asm__ volatile("dmb\\n"); 
//        __asm__ volatile("isb\\n"); 
    }
    return 0;
}

static void __box_mpu_switch(const struct __box_mpuregions *regions) {
//    printf("SHCSR 0x%%08x\\n", *SHCSR);
//    printf("MMFSR 0x%%08x\\n", *(volatile uint32_t*)0xe000ed28);

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

    // TODO
    // clear MemManage error?
    //*SHCSR = *SHCSR & ~0x00010000;
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



