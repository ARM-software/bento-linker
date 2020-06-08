
import itertools as it
import math
from .. import argstuff
from .. import runtimes
from ..box import Fn, Section, Region
from ..runtimes.write_glue import WriteGlue
from ..runtimes.abort_glue import AbortGlue

# utility functions in C
BOX_INIT = """
int32_t __box_init(void) {
    // zero bss
    extern uint32_t __bss_start;
    extern uint32_t __bss_end;
    for (uint32_t *d = &__bss_start; d < &__bss_end; d++) {
        *d = 0;
    }

    // load data
    extern uint32_t __data_init_start;
    extern uint32_t __data_start;
    extern uint32_t __data_end;
    const uint32_t *s = &__data_init_start;
    for (uint32_t *d = &__data_start; d < &__data_end; d++) {
        *d = *s++;
    }

    // init libc
    extern void __libc_init_array(void);
    __libc_init_array();

    return 0;
}
"""

BOX_STRUCT_STATE = """
struct __box_state {
    uint32_t caller;
    uint32_t lr;
    uint32_t *sp;
};
"""

BOX_STRUCT_MPUREGIONS = """
struct __box_mpuregions {
    uint32_t count;
    uint32_t regions[][2];
};
"""

BOX_MPU_DISPATCH = """
#define SHCSR    ((volatile uint32_t*)0xe000ed24)
#define MPU_TYPE ((volatile uint32_t*)0xe000ed90)
#define MPU_CTRL ((volatile uint32_t*)0xe000ed94)
#define MPU_RBAR ((volatile uint32_t*)0xe000ed9c)
#define MPU_RASR ((volatile uint32_t*)0xe000eda0)

static int32_t __box_mpu_init(void) {
    // make sure MPU is initialized
    if (!(*MPU_CTRL & 0x1)) {
        // do we have an MPU?
        assert(*MPU_TYPE >= %(mpuregions)d);
        // enable MemManage exception
        *SHCSR = *SHCSR | 0x00070000;
        // setup call region
        *MPU_RBAR = %(callprefix)#010x | 0x10;
        // disallow execution
        //*MPU_RASR = 0x10230021;
        *MPU_RASR = 0x10000001 | ((%(callregionlog2)d-1) << 1);
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
            *MPU_RBAR = (~0x1f & regions->regions[i][0]) | 0x10 | (i+1);
            *MPU_RASR = regions->regions[i][1];
        } else {
            *MPU_RBAR = 0x10 | (i+1);
            *MPU_RASR = 0;
        }
    }
    *MPU_CTRL = 5;
}
"""

BOX_SYS_DISPATCH = """
struct __box_frame {
    uint32_t *fp;
    uint32_t lr;
    uint32_t *sp;
};

// foward declaration of fault wrapper, may be called directly
// in other handlers, but only in other handlers! (needs isr context)
__attribute__((used, naked, noreturn))
void __box_faulthandler(int32_t err);

#define __BOX_ASSERT(test, code) do {   \\
        if (!(test)) {                  \\
            __box_faulthandler(code);   \\
        }                               \\
    } while (0)

__attribute__((used))
uint64_t __box_callsetup(uint32_t lr, uint32_t *sp,
        uint32_t op, uint32_t *fp) {
    // save lr + sp
    struct __box_state *state = __box_state[__box_active];
    struct __box_frame *frame = (struct __box_frame*)sp;
    frame->fp = fp;
    frame->lr = state->lr;
    frame->sp = state->sp;
    state->lr = lr;
    state->sp = sp;

    uint32_t path = (op & %(callmask)#x)/4;
    uint32_t caller = __box_active;
    __box_active = path %% (__BOX_COUNT+1);
    const uint32_t *targetjumptable = __box_jumptables[__box_active];
    struct __box_state *targetstate = __box_state[__box_active];
    uint32_t targetlr = targetstate->lr;
    uint32_t *targetsp = targetstate->sp;
    // keep track of caller
    targetstate->caller = caller;
    // don't allow returns while executing
    targetstate->lr = 0;
    // need sp to fixup instruction aborts
    targetstate->sp = targetsp;
    uint32_t targetpc = targetjumptable[path / (__BOX_COUNT+1) + 1];

    // select MPU regions
    __box_mpu_switch(__box_mpuregions[__box_active]);

    // enable control?
    uint32_t control;
    __asm__ volatile ("mrs %%0, control" : "=r"(control));
    control = (~1 & control) | (__box_active != 0 ? 1 : 0);
    __asm__ volatile ("msr control, %%0" :: "r"(control));

    // setup new call frame
    targetsp -= 8;
    targetsp[0] = fp[0];        // r0 = arg0
    targetsp[1] = fp[1];        // r1 = arg1
    targetsp[2] = fp[2];        // r2 = arg2
    targetsp[3] = fp[3];        // r3 = arg3
    targetsp[4] = fp[4];        // r12 = r12
    targetsp[5] = %(retprefix)#010x + 1; // lr = __box_ret
    targetsp[6] = targetpc;     // pc = targetpc
    targetsp[7] = fp[7];        // psr = psr

    return ((uint64_t)targetlr) | ((uint64_t)(uint32_t)targetsp << 32);
}

__attribute__((used, naked, noreturn))
void __box_callhandler(uint32_t lr, uint32_t *sp, uint32_t op) {
    __asm__ volatile (
        // keep track of args
        "mov r3, r1 \\n\\t"
        // save core registers
        "stmdb r1!, {r4-r11} \\n\\t"
        // save fp registers?
        "tst r0, #0x10 \\n\\t"
        "it eq \\n\\t"
        "vstmdbeq r1!, {s16-s31} \\n\\t"
        // make space to save state
        "sub r1, r1, #3*4 \\n\\t"
        // sp == msp?
        "tst r0, #0x4 \\n\\t"
        "it eq \\n\\t"
        "moveq sp, r1 \\n\\t"
        // ah! reserve a frame in case we're calling this
        // interrupts stack from another stack
        "sub sp, sp, #8*4 \\n\\t"
        // call into c now that we have stack control
        "bl __box_callsetup \\n\\t"
        // update new sp
        "tst r0, #0x4 \\n\\t"
        "itee eq \\n\\t"
        "msreq msp, r1 \\n\\t"
        "msrne psp, r1 \\n\\t"
        // drop reserved frame?
        "subne sp, sp, #8*4 \\n\\t"
        // return to call
        "bx r0 \\n\\t"
    );
}

__attribute__((used))
uint64_t __box_retsetup(uint32_t lr, uint32_t *sp,
        uint32_t op, uint32_t *fp) {
    // save lr + sp
    struct __box_state *state = __box_state[__box_active];
    // drop exception frame and fixup instruction aborts
    sp = state->sp;
    state->lr = lr;
    state->sp = sp;

    __box_active = state->caller;
    struct __box_state *targetstate = __box_state[__box_active];
    uint32_t targetlr = targetstate->lr;
    __BOX_ASSERT(targetlr, BOX_ERR_FAULT); // in call?
    uint32_t *targetsp = targetstate->sp;
    struct __box_frame *targetframe = (struct __box_frame*)targetsp;
    uint32_t *targetfp = targetframe->fp;
    targetstate->lr = targetframe->lr;
    targetstate->sp = targetframe->sp;

    // select MPU regions
    __box_mpu_switch(__box_mpuregions[__box_active]);

    // enable control?
    uint32_t control;
    __asm__ volatile ("mrs %%0, control" : "=r"(control));
    control = (~1 & control) | (__box_active != 0 ? 1 : 0);
    __asm__ volatile ("msr control, %%0" :: "r"(control));

    // copy return frame
    targetfp[0] = fp[0];       // r0 = arg0
    targetfp[1] = fp[1];       // r1 = arg1
    targetfp[2] = fp[2];       // r2 = arg2
    targetfp[3] = fp[3];       // r3 = arg3
    targetfp[6] = targetfp[5]; // pc = lr

    return ((uint64_t)targetlr) | ((uint64_t)(uint32_t)targetsp << 32);
}

__attribute__((used, naked, noreturn))
void __box_rethandler(uint32_t lr, uint32_t *sp, uint32_t op) {
    __asm__ volatile (
        // keep track of rets
        "mov r3, r1 \\n\\t"
        // call into c new that we have stack control
        "bl __box_retsetup \\n\\t"
        // drop saved state
        "add r1, r1, #3*4 \\n\\t"
        // restore fp registers?
        "tst r0, #0x10 \\n\\t"
        "it eq \\n\\t"
        "vldmiaeq r1!, {s16-s31} \\n\\t"
        // restore core registers
        "ldmia r1!, {r4-r11} \\n\\t"
        // update sp
        "tst r0, #0x4 \\n\\t"
        "ite eq \\n\\t"
        "msreq msp, r1 \\n\\t"
        "msrne psp, r1 \\n\\t"
        // return
        "bx r0 \\n\\t"
    );
}

__attribute__((used))
uint64_t __box_faultsetup(int32_t err) {
    // invoke user handler, may not return
    // TODO should we set this up to be called in non-isr context?
    __box_faults[__box_active](err);

    struct __box_state *state = __box_state[__box_active];
    struct __box_state *targetstate = __box_state[state->caller];
    uint32_t targetlr = targetstate->lr;
    uint32_t *targetsp = targetstate->sp;
    struct __box_frame *targetbf = (struct __box_frame*)targetsp;
    uint32_t *targetfp = targetbf->fp;
    // in call?
    if (!targetlr) {
        // halt if not handled
        while (1) {}
    }

    // check if our return target supports erroring
    uint32_t op = targetfp[6];
    if (!(op & 2)) {
        // halt if not handled
        while (1) {}
    }

    // we can return an error
    __box_active = state->caller;
    targetstate->lr = targetbf->lr;
    targetstate->sp = targetbf->sp;

    // select MPU regions
    __box_mpu_switch(__box_mpuregions[__box_active]);

    // enable control?
    uint32_t control;
    __asm__ volatile ("mrs %%0, control" : "=r"(control));
    control = (~1 & control) | (__box_active != 0 ? 1 : 0);
    __asm__ volatile ("msr control, %%0" :: "r"(control));

    // copy return frame
    targetfp[0] = err;         // r0 = arg0
    targetfp[1] = 0;           // r1 = arg1
    targetfp[2] = 0;           // r2 = arg2
    targetfp[3] = 0;           // r3 = arg3
    targetfp[6] = targetfp[5]; // pc = lr

    return ((uint64_t)targetlr) | ((uint64_t)(uint32_t)targetsp << 32);
}

__attribute__((used, naked, noreturn))
void __box_faulthandler(int32_t err) {
    __asm__ volatile (
        // call into c with stack control
        "bl __box_faultsetup \\n\\t"
        // drop saved state
        "add r1, r1, #3*4 \\n\\t"
        // restore fp registers?
        "tst r0, #0x10 \\n\\t"
        "it eq \\n\\t"
        "vldmiaeq r1!, {s16-s31} \\n\\t"
        // restore core registers
        "ldmia r1!, {r4-r11} \\n\\t"
        // update sp
        "tst r0, #0x4 \\n\\t"
        "ite eq \\n\\t"
        "msreq msp, r1 \\n\\t"
        "msrne psp, r1 \\n\\t"
        // return
        "bx r0 \\n\\t"
    );
}

__attribute__((alias("__box_mpu_handler")))
void __box_usagefault_handler(void);
__attribute__((alias("__box_mpu_handler")))
void __box_busfault_handler(void);
__attribute__((alias("__box_mpu_handler")))
void __box_memmanage_handler(void);
__attribute__((naked))
void __box_mpu_handler(void) {
    __asm__ volatile (
        // get lr
        "mov r0, lr \\n\\t"
        "tst r0, #0x4 \\n\\t"
        // get sp
        "ite eq \\n\\t"
        "mrseq r1, msp \\n\\t"
        "mrsne r1, psp \\n\\t"
        // get pc
        "ldr r2, [r1, #6*4] \\n\\t"
        // call?
        "ldr r3, =#%(callprefix)#010x \\n\\t"
        "sub r3, r2, r3 \\n\\t"
        "lsrs r3, r3, #%(callregionlog2)d-1 \\n\\t"
        "beq __box_callhandler \\n\\t"
        // ret?
        "ldr r3, =#%(retprefix)#010x \\n\\t"
        "subs r3, r2, r3 \\n\\t"
        "beq __box_rethandler \\n\\t"
        // fallback to fault handler
        // explicit fault?
        "ldr r3, =#%(retprefix)#010x + 1*4 \\n\\t"
        "subs r3, r2, r3 \\n\\t"
        "ite eq \\n\\t"
        "ldreq r0, [r1, #0] \\n\\t"
        "ldrne r0, =%%0 \\n\\t"
        "b __box_faulthandler \\n\\t"
        :
        : "i"(BOX_ERR_FAULT)
    );
}
"""

BOX_SYS_INIT = """
int __box_%(box)s_init(void) {
    int32_t err = __box_mpu_init();
    if (err) {
        return err;
    }

    // prepare box's stack
    // must use PSP, otherwise boxes could overflow ISR stack
    __box_%(box)s_state.lr = 0xfffffffd; // TODO determine fp?
    __box_%(box)s_state.sp = (uint32_t*)__box_%(box)s_jumptable[0];

    // call box's init
    extern int __box_%(box)s_rawinit(void);
    return __box_%(box)s_rawinit();
}
"""

@runtimes.runtime
class ARMv7MMPURuntime(WriteGlue, AbortGlue, runtimes.Runtime):
    """
    A bento-box runtime that uses a v7 MPU to provide memory isolation
    between boxes.
    """
    __argname__ = "armv7m_mpu"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser, **kwargs):
        parser.add_argument("--mpu_regions", type=int,
            help="Upper limit on the number of MPU regions to manage for "
                "each box. Note the actual number of MPU regions will be "
                "this plus one region for box calls. Defualts to 4.")
        parser.add_nestedparser('--jumptable', Section)
        parser.add_nestedparser('--call_region', Region)

    def __init__(self, mpu_regions=None, jumptable=None, call_region=None):
        super().__init__()
        self._mpu_regions = mpu_regions if mpu_regions is not None else 4
        self._jumptable = Section('jumptable', **jumptable.__dict__)
        self._call_region = (
            Region(**call_region.__dict__)
            if call_region.addr is not None else
            Region('0x1e000000-0x1fffffff'))

    __name = __argname__
    def box_parent_prologue(self, parent):
        parent.addexport('__box_memmanage_handler', 'fn() -> void',
            target=parent.name, source=self.__name)
        parent.addexport('__box_busfault_handler', 'fn() -> void',
            target=parent.name, source=self.__name)
        parent.addexport('__box_usagefault_handler', 'fn() -> void',
            target=parent.name, source=self.__name)

        # we collect hooks here because we need to handle them all at once
        self._fault_hooks = []
        self._write_hooks = []
        for child in parent.boxes:
            if child.runtime == self:
                self._fault_hooks.append(parent.addimport(
                    '__box_%s_fault' % child.name, 'fn(err32) -> void',
                    target=parent.name, source=self.__name, weak=True,
                    doc="Called when this box faults, either due to an illegal "
                        "memory access or other failure. the error code is "
                        "provided as an argument."))
                self._write_hooks.append(parent.addimport(
                    '__box_%s_write' % child.name, 'fn(err32) -> void',
                    target=parent.name, source=self.__name, weak=True,
                    doc="Override __box_write for this specific box."))

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

        for memory in box.memories:
            assert math.log2(memory.size) % 1 == 0, (
                "Memory region %r not aligned to a power-of-two"
                    % memory.name)
            assert memory.addr % memory.size == 0, (
                "Memory region %r not aligned to its size"
                    % memory.name)
            assert memory.size >= 32, (
                "Memory region %r too small (< 32 bytes)"
                    % memory.name)

        parent.addimport(
            '__box_init', 'fn() -> err32',
            target=box.name, source=self.__name,
            alias='__box_%s_rawinit' % box.name)
        parent.addexport(
            '__box_%s_write' % box.name, 'fn(i32, u8*, usize) -> errsize',
            target=box.name, source=self.__name)

    def box_box(self, box):
        self._jumptable.alloc(box, 'r')
        # plumbing
        box.addexport(
            '__box_init', 'fn() -> err32',
            source=self.__name)
        box.addimport(
            '__box_%s_write' % box.name, 'fn(i32, u8*, usize) -> errsize',
            source=self.__name)
        # plugs
        self._abort_plug = box.addexport(
            '__box_abort', 'fn(err32) -> void',
            target=box.name, source=self.__name, weak=True)
        self._write_plug = box.addexport(
            '__box_write', 'fn(i32, u8*, usize) -> errsize',
            target=box.name, source=self.__name, weak=True)

        super().box_box(box)

    # overridable
    def build_mpu_dispatch(self, output, sys):
        output.decls.append(BOX_STRUCT_MPUREGIONS)
        output.decls.append(BOX_MPU_DISPATCH)

    # overridable
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
                    out.printf('{%(rbar)#010x, %(rasr)#010x},',
                        rbar=memory.addr,
                        rasr= (0x10000000
                                if 'x' not in memory.mode else
                                0x00000000)
                            | (0x03000000
                                if set('rw').issubset(memory.mode) else
                                0x02000000
                                if 'r' in memory.mode else
                                0x00000000)
                            | 0 #(0x00080000)
                            | ((int(math.log2(memory.size))-1) << 1)
                            | 1)
            out.printf('},')
        out.printf('};')

    def build_parent_ld_prologue(self, output, sys):
        super().build_parent_ld_prologue(output, sys)

        out = output.decls.append(doc='box calls')
        for import_ in sys.imports:
            if import_.link and import_.link.export.box != sys:
                out.printf(
                    '%(import_)-16s = %(callprefix)#010x + '
                        '%(id)d*4 + %(falible)d*2 + 1;',
                    import_=import_.alias,
                    id=import_.link.export.n()*(len(sys.boxes)+1) +
                        import_.link.export.box.n()+1,
                    falible=import_.isfalible())

    def build_parent_c_prologue(self, output, sys):
        output.decls.append('//// jumptable implementation ////')
        self.build_mpu_dispatch(output, sys)

        out = output.decls.append(doc='System state')
        out.printf('uint32_t __box_active = 0;')

        # redirect writes if necessary
        if any(not write_hook.link for write_hook in self._write_hooks):
            out = output.decls.append(doc='Redirected __box_writes')
            for write_hook in self._write_hooks:
                if not write_hook.link:
                    out.printf('#define %(write_hook)s __box_write',
                        write_hook=write_hook.linkname)

        # jumptables
        out = output.decls.append(doc='Jumptables')
        out.printf('const uint32_t __box_sys_jumptable[] = {')
        with out.pushindent():
            out.printf('(uint32_t)NULL, // no stack for sys')
            for export in sys.exports:
                out.printf('(uint32_t)%(export)s,', export=export.alias)
        out.write('};')

        out = output.decls.append()
        for box in sys.boxes:
            if box.runtime == self:
                out.printf(
                    'extern const uint32_t __box_%(box)s_jumptable[];',
                    box=box.name)

        out = output.decls.append()
        out.printf('#define __BOX_COUNT %(boxcount)d',
            boxcount=sum(1 for box in sys.boxes
                if box.runtime == self))
        out.printf('const uint32_t *const '
            '__box_jumptables[__BOX_COUNT+1] = {');
        with out.pushindent():
            out.printf('__box_sys_jumptable,')
            for box in sys.boxes:
                if box.runtime == self:
                    out.printf('__box_%(box)s_jumptable,',
                        box=box.name)
        out.printf('};');

        # mpu regions
        out = output.decls.append()
        out.printf('const struct __box_mpuregions __box_sys_mpuregions = {')
        with out.pushindent():
            out.printf('.count = 0,')
            out.printf('.regions = {},')
        out.printf('};')

        for box in sys.boxes:
            if box.runtime == self:
                self.build_mpu_regions(output, sys, box)

        out = output.decls.append()
        out.printf('const struct __box_mpuregions *const '
            '__box_mpuregions[__BOX_COUNT+1] = {')
        with out.pushindent():
            out.printf('&__box_sys_mpuregions,')
            for box in sys.boxes:
                if box.runtime == self:
                    out.printf('&__box_%(box)s_mpuregions,', box=box.name)
        out.printf('};')

        # fault handlers
        for fault_hook, child in zip(self._fault_hooks, (
                child for child in sys.boxes
                if child.runtime == self)):
            if not fault_hook.link:
                out.printf('__attribute__((used))')
                out.printf('void __box_%(box)s_fault(int err) {}',
                    box=child.name)

        out = output.decls.append()
        out.printf('void (*const __box_faults[__BOX_COUNT+1])(int err) = {')
        with out.indent():
            out.printf('&__box_abort,', box=box.name)
            for fault_hook in self._fault_hooks:
                out.printf('&%(fault_hook)s,',
                    fault_hook=fault_hook.link.export.alias
                        if fault_hook.link else
                        fault_hook.linkname)
        out.printf('};')

        # state
        output.decls.append(BOX_STRUCT_STATE, doc='Box state')
        out = output.decls.append()
        out.printf('struct __box_state __box_sys_state;')
        for box in sys.boxes:
            if box.runtime == self:
                out.printf('struct __box_state __box_%(box)s_state;',
                    box=box.name)

        out = output.decls.append()
        out.printf('struct __box_state *const __box_state[__BOX_COUNT+1] = {')
        with out.indent():
            out.printf('&__box_sys_state,', box=box.name)
            for box in sys.boxes:
                if box.runtime == self:
                    out.printf('&__box_%(box)s_state,', box=box.name)
        out.printf('};')

        # the rest of the dispatch logic
        output.includes.append('<assert.h>') # TODO need this?
        output.decls.append(BOX_SYS_DISPATCH, doc='Dispach logic')

    def build_parent_ld(self, output, sys, box):
        super().build_parent_ld(output, sys, box)

        if output.emit_sections:
            out = output.sections.append(
                box_memory=self._jumptable.memory.name,
                section='.box.%(box)s.%(box_memory)s',
                memory='box_%(box)s_%(box_memory)s')
            out.printf('__box_%(box)s_jumptable = __%(memory)s_start;')

    def build_parent_c(self, output, sys, box):
        output.decls.append('//// %(box)s init ////')
        output.decls.append(BOX_SYS_INIT)

    def build_box_ld(self, output, box):
        # create box calls for imports
        out = output.decls.append(doc='box calls')
        for import_ in box.imports:
            if import_.link and import_.link.export.box != box:
                out.printf(
                    '%(import_)-16s = %(callprefix)#010x + '
                        '%(id)d*4 + %(falible)d*2 + 1;',
                    import_=import_.alias,
                    id=import_.link.export.n()*(len(box.parent.boxes)+1),
                    falible=import_.isfalible())

        out = output.decls.append(doc='special box triggers')
        out.printf('%(name)-16s = %(retprefix)#010x + 1;',
            name='__box_ret')
        if self._abort_plug.links:
            out.printf('%(name)-16s = %(retprefix)#010x + %(id)d*4 + 1;',
                name='__box_abort',
                id=1)
        if self._write_plug.links:
            out.printf('%(name)-16s = __box_%(box)s_write;',
                name='__box_write')

        if output.emit_sections:
            out = output.sections.append(
                section='.jumptable',
                memory=self._jumptable.memory.name)
            out.printf('%(section)s : {')
            with out.pushindent():
                out.printf('. = ALIGN(%(align)d);')
                out.printf('__jumptable_start = .;')
                out.printf('__jumptable = .;')
                out.printf('KEEP(*(.jumptable))')
                out.printf('. = ALIGN(%(align)d);')
                out.printf('__jumptable_end = .;')
            out.printf('} > %(MEMORY)s')

        super().build_box_ld(output, box)

    def build_box_c(self, output, box):
        super().build_box_c(output, box)

        output.decls.append('//// jumptable implementation ////')
        output.decls.append(BOX_INIT)

        output.decls.append('extern uint32_t __stack_end;')
        out = output.decls.append(doc='box-side jumptable')
        out.printf('__attribute__((section(".jumptable")))')
        out.printf('__attribute__((used))')
        out.printf('const uint32_t __box_%(box)s_jumptable[] = {')
        with out.pushindent():
            # special entries for the sp and __box_init
            out.printf('(uint32_t)&__stack_end,')
            for export in box.exports:
                out.printf('(uint32_t)%(export)s,', export=export.alias)
        out.printf('};')

