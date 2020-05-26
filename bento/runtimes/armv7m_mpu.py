
import itertools as it
import math
from .. import argstuff
from .. import runtimes
from ..box import Fn, Region

# utility functions in C
BOX_INIT = """
static void __box_%(box)s_init() {
    // zero bss
    extern uint32_t __bss;
    extern uint32_t __bss_end;
    for (uint32_t *d = &__bss; d < &__bss_end; d++) {
        *d = 0;
    }

    // load data
    extern uint32_t __data_init;
    extern uint32_t __data;
    extern uint32_t __data_end;
    const uint32_t *s = &__data_init;
    for (uint32_t *d = &__data; d < &__data_end; d++) {
        *d = *s++;
    }
}
"""

BOX_WRITE = """
//__attribute__((alias("__box_write")))
int _write(int handle, char *buffer, int size) {
    extern int __box_write(int handle, char *buffer, int size);
    // TODO hmm, why can't this alias?
    return __box_write(handle, buffer, size);
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
        *SHCSR = *SHCSR | 0x00010000;
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
__attribute__((naked, noreturn))
void __box_faulthandler(int32_t err);

#define __BOX_ASSERT(test, code) do {   \\
        if (!(test)) {                  \\
            __box_faulthandler(code);   \\
        }                               \\
    } while (0)

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

__attribute__((naked, noreturn))
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

__attribute__((naked, noreturn))
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

__attribute__((naked, noreturn))
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

__attribute__((alias("MemManage_Handler")))
void BusFault_Handler(void);
__attribute__((naked))
void MemManage_Handler(void) {
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
        // explicit fault?
        "ldr r3, =#%(retprefix)#010x + 1*4 \\n\\t"
        "subs r3, r2, r3 \\n\\t"
        "beq __box_faulthandler \\n\\t"
        // fallback to fault handler
        "ldr r0, =%%0 \\n\\t"
        "b __box_faulthandler \\n\\t"
        :
        : "i"(BOX_ERR_FAULT)
    );
}
"""

BOX_SYS_INIT = """
extern int32_t __box_%(box)s_rawinit(void);
int32_t __box_%(box)s_init(void) {
    int32_t err = __box_mpu_init();
    if (err) {
        return err;
    }

    // prepare box's stack
    // must use PSP, otherwise boxes could overflow ISR stack
    __box_%(box)s_state.lr = 0xfffffffd; // TODO determine fp?
    __box_%(box)s_state.sp = (uint32_t*)__box_%(box)s_jumptable[0];

    // call box's init
    return __box_%(box)s_rawinit();
}
"""

@runtimes.runtime
class ARMv7MMPURuntime(runtimes.Runtime):
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
        parser.add_nestedparser('--call_region', Region)

    def __init__(self, mpu_regions=None, call_region=None):
        super().__init__()
        self.ids = {}
        self._mpu_regions = mpu_regions if mpu_regions is not None else 4
        self._call_region = (
            Region(**call_region.__dict__)
            if call_region else
            Region('0x1e000000-0x1fffffff'))

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
                    assert math.log2(memory.size) % 1 == 0, (
                        "Memory region %s not aligned to a power-of-two"
                            % memory.name)
                    assert memory.addr % memory.size == 0, (
                        "Memory region %s not aligned to its size"
                            % memory.name)
                    assert memory.size >= 32, (
                        "Memory region %s too small (< 32 bytes)"
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

    def build_parent_prologue_c(self, output, sys):
        output.decls.append('//// jumptable implementation ////')
        output.decls.append(
            'extern int _write(int handle, char *buffer, int size);',
            doc='GCC stdlib hook')

        self.build_mpu_dispatch(output, sys)

        out = output.decls.append(doc='System state')
        out.printf('uint32_t __box_active = 0;')

        # jumptables
        out = output.decls.append(doc='Jumptables')
        out.printf('const uint32_t __box_sys_jumptable[] = {')
        with out.pushindent():
            out.printf('(uint32_t)NULL, // no stack for sys')
            out.printf('(uint32_t)&_write,')
            for export in sys.exports:
                out.printf('(uint32_t)%(export)s,', export=export.name)
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
        out = output.decls.append()
        out.printf('void __box_sys_fault(int32_t err) {')
        with out.indent():
            # TODO print if write is hooked up?
            out.printf('// system must halt, no way to recover')
            out.printf('while (1) {}')
        out.printf('}')

        for box in sys.boxes:
            if box.runtime == self:
                out = output.decls.append(box=box.name)
                out.printf('__attribute__((weak))')
                out.printf('void __box_%(box)s_fault(int32_t err) {')
                with out.indent():
                    # TODO print if write is hooked up?
                    out.printf('// overridable by user')
                out.printf('}')

        out = output.decls.append()
        out.printf('void (*const '
            '__box_faults[__BOX_COUNT+1])(int32_t err) = {')
        with out.indent():
            out.printf('&__box_sys_fault,', box=box.name)
            for box in sys.boxes:
                if box.runtime == self:
                    out.printf('&__box_%(box)s_fault,', box=box.name)
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

    def build_parent_c(self, output, sys, box):
        output.decls.append(BOX_SYS_INIT)

    def build_box_c(self, output, box):
        super().build_box_c(output, box)
        output.decls.append('//// jumptable declarations ////')

        out = output.decls.append()
        out.printf('struct %(box)s_exportjumptable {')
        with out.pushindent():
            # special entries for the sp and __box_init
            out.printf('uint32_t *__box_%(box)s_stack_end;')
            out.printf('void (*__box_%(box)s_init)(void);')
            for export in box.exports:
                out.printf('%(fn)s;', fn=export.repr_c_ptr())
        out.printf('};')

        output.decls.append('//// jumptable implementation ////')
        output.decls.append(BOX_INIT)
        output.decls.append(BOX_WRITE)

        output.decls.append('extern uint32_t __stack_end;')
        out = output.decls.append(doc='box-side jumptable')
        out.printf('__attribute__((section(".jumptable")))')
        out.printf('__attribute__((used))')
        out.printf('const struct %(box)s_exportjumptable '
            '__box_%(box)s_jumptable = {')
        with out.pushindent():
            # special entries for the sp and __box_init
            out.printf('&__stack_end,')
            out.printf('__box_%(box)s_init,')
            for export in box.exports:
                out.printf('%(export)s,', export=export.name)
        out.printf('};')

    def build_parent_partial_ld(self, output, sys, box):
        # create box calls for imports
        output.decls.append('/* box calls */')
        for import_ in it.chain(
                # TODO rename this
                [Fn('__box_%s_rawinit' % box.name, 'fn() -> err32')],
                (import_ for import_ in box.exports)):
            output.decls.append(
                '%(import_)-24s = %(callprefix)#010x + '
                    '%(id)d*4 + %(falible)d*2 + 1;',
                import_=import_.name,
                id=self.ids[import_.name],
                falible=import_.isfalible())
        output.decls.append()

        memory, _, _ = box.consume('rx', box.jumptable.size)
        out = output.sections.insert(0,
            box_memory=memory.name,
            section='.box.%(box)s.%(box_memory)s',
            memory='box_%(box)s_%(box_memory)s')
        out.printf('. = ORIGIN(%(MEMORY)s);')
        out.printf('__box_%(box)s_jumptable = .;')
        super().build_parent_partial_ld(output, sys, box)

    def build_parent_ld(self, output, sys, box):
        return self.build_parent_partial_ld(output, sys, box)

    def build_box_partial_ld(self, output, box):
        # create box calls for imports
        out = output.decls.append(doc='box calls')
        for i, import_ in enumerate(it.chain(
                [Fn('__box_write', 'fn(i32, u8*, usize) -> err32')],
                (import_ for import_ in box.imports))):
            out.printf(
                '%(import_)-24s = %(callprefix)#010x + '
                    '%(id)d*4 + %(falible)d*2 + 1;',
                import_=import_.name,
                id=self.ids[import_.name],
                falible=import_.isfalible())

        out = output.decls.append(doc='special box triggers')
        out.printf('%(name)-24s = %(retprefix)#010x + 1;',
            name='__box_ret')
        out.printf('%(name)-24s = %(retprefix)#010x + %(id)d*4 + 1;',
            name='__box_fault',
            id=1)

    def build_box_ld(self, output, box):
        self.build_box_partial_ld(output, box)
        
        memory, _, _ = box.consume('rx', section=box.jumptable)
        out = output.sections.insert(0,
            section='.jumptable',
            memory=memory.name)
        out.printf('%(section)s : {')
        with out.pushindent():
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__jumptable = .;')
            out.printf('KEEP(*(.jumptable))')
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__jumptable_end = .;')
        out.printf('} > %(MEMORY)s')

        super().build_box_ld(output, box)

