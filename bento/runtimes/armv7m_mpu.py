
import itertools as it
import math
from .. import argstuff
from .. import runtimes
from ..box import Fn, Section, Region, Import, Export
from ..glue.error_glue import ErrorGlue
from ..glue.write_glue import WriteGlue
from ..glue.abort_glue import AbortGlue
from ..glue.heap_glue import HeapGlue
from ..outputs import OutputBlob

MPU_STATE = """
uint32_t __box_active = 0;
extern uint32_t __box_callregion;
extern void __box_return(void);
"""

MPU_IMPL = """
#define SHCSR    ((volatile uint32_t*)0xe000ed24)
#define MPU_TYPE ((volatile uint32_t*)0xe000ed90)
#define MPU_CTRL ((volatile uint32_t*)0xe000ed94)
#define MPU_RBAR ((volatile uint32_t*)0xe000ed9c)
#define MPU_RASR ((volatile uint32_t*)0xe000eda0)

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
        // enable MemManage exceptions
        *SHCSR = *SHCSR | 0x00070000;
        // setup call region
        *MPU_RBAR = (uint32_t)&__box_callregion | 0x10;
        // disallow execution
        *MPU_RASR = 0x10000001 | ((%(calllog2)d-1) << 1);
        // enable the MPU
        *MPU_CTRL = 5;
    }
    return 0;
}

static void __box_mpu_switch(const struct __box_mpuregions *regions) {
    // update MPU regions
    *MPU_CTRL = 0;
    uint32_t count = regions->count;
    for (int i = 0; i < %(mpuregions)d; i++) {
        if (i < count) {
            *MPU_RBAR = regions->regions[i][0] | 0x10 | (i+1);
            *MPU_RASR = regions->regions[i][1];
        } else {
            *MPU_RBAR = 0x10 | (i+1);
            *MPU_RASR = 0;
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

BOX_STATE = """
struct __box_state {
    bool initialized;
    uint32_t caller;
    uint32_t lr;
    uint32_t *sp;
};
"""

MPU_HANDLERS = """
struct __box_frame {
    uint32_t *fp;
    uint32_t lr;
    uint32_t *sp;
    uint32_t caller;
};

// foward declaration of fault wrapper, may be called directly
// in other handlers, but only in other handlers! (needs isr context)
uint64_t __box_faultsetup(int32_t err) {
    // mark box as uninitialized
    __box_state[__box_active]->initialized = false;

    // invoke user handler, should not return
    // TODO should we set this up to be called in non-isr context?
    if (__box_aborts[__box_active]) {
        __box_aborts[__box_active](err);
        __builtin_unreachable();
    }

    struct __box_state *state = __box_state[__box_active];
    struct __box_state *targetstate = __box_state[state->caller];
    uint32_t targetlr = targetstate->lr;
    uint32_t *targetsp = targetstate->sp;
    struct __box_frame *targetbf = (struct __box_frame*)targetsp;
    uint32_t *targetfp = targetbf->fp;
    // in call?
    if (!targetlr) {
        // halt if we can't handle
        __box_abort(-ELOOP);
    }

    // check if our return target supports erroring
    uint32_t op = targetfp[6];
    if (!(op & 2)) {
        // halt if we can't handle
        __box_abort(err);
    }

    // we can return an error
    __box_active = state->caller;
    targetstate->lr = targetbf->lr;
    targetstate->sp = targetbf->sp;
    targetstate->caller = targetbf->caller;

    // select MPU regions
    __box_mpu_switch(__box_mpuregions[__box_active]);

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
        "add r1, r1, #4*4 \\n\\t"
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
        ::
        "i"(__box_faultsetup)
    );
}

uint64_t __box_callsetup(uint32_t lr, uint32_t *sp,
        uint32_t op, uint32_t *fp) {
    // save lr + sp
    struct __box_state *state = __box_state[__box_active];
    struct __box_frame *frame = (struct __box_frame*)sp;
    frame->fp = fp;
    frame->lr = state->lr;
    frame->sp = state->sp;
    frame->caller = state->caller;
    state->lr = lr;
    state->sp = sp;

    uint32_t caller = __box_active;
    __box_active = (caller == 0)
        ? (((op/4)-2) %% __BOX_COUNT) + 1
        : 0;
    uint32_t targetpc = (caller == 0)
        ? __box_jumptables[__box_active-1][((op/4)-2) / __BOX_COUNT + 1]
        : __box_sys_jumptables[caller-1][((op/4)-2)];
    struct __box_state *targetstate = __box_state[__box_active];
    uint32_t targetlr = targetstate->lr;
    uint32_t *targetsp = targetstate->sp;
    // keep track of caller
    targetstate->caller = caller;
    // don't allow returns while executing
    targetstate->lr = 0;
    // need sp to fixup instruction aborts
    targetstate->sp = targetsp;

    // select MPU regions
    __box_mpu_switch(__box_mpuregions[__box_active]);

    // setup new call frame
    targetsp -= 8;
    targetsp[0] = fp[0];        // r0 = arg0
    targetsp[1] = fp[1];        // r1 = arg1
    targetsp[2] = fp[2];        // r2 = arg2
    targetsp[3] = fp[3];        // r3 = arg3
    targetsp[4] = fp[4];        // r12 = r12
    targetsp[5] = (uint32_t)&__box_return; // lr = __box_return
    targetsp[6] = targetpc;     // pc = targetpc
    targetsp[7] = fp[7];        // psr = psr

    return ((uint64_t)targetlr) | ((uint64_t)(uint32_t)targetsp << 32);
}

__attribute__((naked))
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
        "sub r1, r1, #4*4 \\n\\t"
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
        "addne sp, sp, #8*4 \\n\\t"
        // return to call
        "bx r0 \\n\\t"
        ::
        "i"(__box_callsetup)
    );
}

uint64_t __box_returnsetup(uint32_t lr, uint32_t *sp,
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
    // in call?
    if (!targetlr) {
        __box_faulthandler(-EFAULT);
        __builtin_unreachable();
    }
    uint32_t *targetsp = targetstate->sp;
    struct __box_frame *targetframe = (struct __box_frame*)targetsp;
    uint32_t *targetfp = targetframe->fp;
    targetstate->lr = targetframe->lr;
    targetstate->sp = targetframe->sp;
    targetstate->caller = targetframe->caller;

    // select MPU regions
    __box_mpu_switch(__box_mpuregions[__box_active]);

    // copy return frame
    targetfp[0] = fp[0];       // r0 = arg0
    targetfp[1] = fp[1];       // r1 = arg1
    targetfp[2] = fp[2];       // r2 = arg2
    targetfp[3] = fp[3];       // r3 = arg3
    targetfp[6] = targetfp[5]; // pc = lr

    return ((uint64_t)targetlr) | ((uint64_t)(uint32_t)targetsp << 32);
}

__attribute__((naked, noreturn))
void __box_returnhandler(uint32_t lr, uint32_t *sp, uint32_t op) {
    __asm__ volatile (
        // keep track of rets
        "mov r3, r1 \\n\\t"
        // call into c new that we have stack control
        "bl __box_returnsetup \\n\\t"
        // drop saved state
        "add r1, r1, #4*4 \\n\\t"
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
        ::
        "i"(__box_returnsetup)
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

        // check type of call
        // return?
        "ldr r3, =__box_callregion \\n\\t"
        "subs r2, r2, r3 \\n\\t"
        "beq __box_returnhandler \\n\\t"

        // explicit abort?
        "cmp r2, #4 \\n\\t"
        "itt eq \\n\\t"
        "ldreq r0, [r1, #0] \\n\\t"
        "beq __box_faulthandler \\n\\t"

        // call?
        "ldr r3, =%(callsize)d \\n\\t"
        "cmp r2, r3 \\n\\t"
        "blo __box_callhandler \\n\\t"

        // if we've reached here this is a true fault
        "ldr r0, =%%[EFAULT] \\n\\t"
        "b __box_faulthandler \\n\\t"
        "b ."
        ::
        "i"(__box_faulthandler),
        "i"(__box_callhandler),
        "i"(__box_returnhandler),
        "i"(&__box_callregion),
        [EFAULT]"i"(-EFAULT)
    );
}
"""


@runtimes.runtime
class ARMv7MMPURuntime(
        ErrorGlue,
        WriteGlue,
        AbortGlue,
        HeapGlue,
        runtimes.Runtime):
    """
    A bento-box runtime that uses an Arm v7 MPU to provide memory isolation
    between boxes.
    """
    __argname__ = "armv7m_mpu"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser, **kwargs):
        parser.add_argument('--mpu_regions', type=int,
            help="Upper limit on the number of MPU regions to manage for "
                "each box. Note the actual number of MPU regions will be "
                "this plus one region for box calls. Defualts to 4.")
        parser.add_nestedparser('--jumptable', Section)
        parser.add_nestedparser('--call_region', Region)
        parser.add_argument('--zero', type=bool,
            help="Zero RAM before executing the box. This is useful if boxes "
                "share RAM to avoid leaking data. This is not useful if the "
                "box is the only box able to access its allocated RAM.")

    def __init__(self, mpu_regions=None, jumptable=None,
            call_region=None, zero=None):
        super().__init__()
        self._mpu_regions = mpu_regions if mpu_regions is not None else 4
        self._jumptable = Section('jumptable', **jumptable.__dict__)
        self._call_region = (Region(**call_region.__dict__)
            if call_region.addr is not None else
            None)
        self._zero = zero or False

    # overridable
    def _box_call_region(self, parent):
        callmemory = parent.bestmemory(
            'rx', size=0, reverse=True).origmemory
        addr = callmemory.addr + callmemory.size

        # TODO fewer magic numbers here?
        importcount = max(it.chain(
            [3+sum(len(box.exports)
                for box in parent.boxes
                if box.runtime == self)],
            (4+len(box.imports)
                for box in parent.boxes
                if box.runtime == self)))
        # fit into MPU limits
        size = 2**math.ceil(math.log2(4*importcount))
        size = max(size, 32)

        return Region(addr=addr, size=size)

    # overridable
    def _check_call_region(self, call_region):
        assert math.log2(call_region.size) % 1 == 0, (
            "%s: MPU call region not aligned to a power-of-two `%s`"
                % (self.name, call_region))
        assert call_region.addr % call_region.size == 0, (
            "%s: MPU call region not aligned to size `%s`"
                % (self.name, call_region))
        assert call_region.size >= 32, (
            "%s: MPU call region too small (< 32 bytes) `%s`"
                % (self.name, call_region))

    # overridable
    def _check_mpu_region(self, memory):
        assert math.log2(memory.size) % 1 == 0, (
            "%s: Memory region `%s` not aligned to a power-of-two `%s`"
                % (box.name, memory.name, memory))
        assert memory.addr % memory.size == 0, (
            "%s: Memory region `%s` not aligned to its size `%s`"
                % (box.name, memory.name, memory))
        assert memory.size >= 32, (
            "%s: Memory region `%s` too small (< 32 bytes) `%s`"
                % (box.name, memory.name, memory))

    # overridable
    def _build_mpu_impl(self, output, parent):
        output.decls.append(MPU_IMPL)

    # overridable
    def _build_mpu_sysregions(self, output, parent):
        out = output.decls.append()
        out.printf('const struct __box_mpuregions __box_sys_mpuregions = {')
        with out.pushindent():
            out.printf('.control = 0,')
            out.printf('.count = 0,')
            out.printf('.regions = {}')
        out.printf('};')

    # overridable
    def _build_mpu_regions(self, output, parent, box):
        out = output.decls.append()
        out.printf('const struct __box_mpuregions __box_%(box)s_mpuregions = {')
        with out.pushindent():
            out.printf('.control = 1,')
            out.printf('.count = %(count)d,', count=len(box.memories))
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

    def box_parent_prologue(self, parent):
        # we need these
        parent.addexport('__box_memmanage_handler', 'fn() -> void',
            scope=parent.name, source=self.__argname__)
        parent.addexport('__box_busfault_handler', 'fn() -> void',
            scope=parent.name, source=self.__argname__)
        parent.addexport('__box_usagefault_handler', 'fn() -> void',
            scope=parent.name, source=self.__argname__)

        super().box_parent_prologue(parent)

        # best effort call_region size
        if self._call_region is None:
            self._call_region = self._box_call_region(parent)

        # check our call region
        self._check_call_region(self._call_region)

        parent.pushattrs(
            mpuregions=self._mpu_regions,
            callregion=self._call_region.addr,
            callsize=self._call_region.addr,
            callmask=self._call_region.size-1,
            calllog2=math.log2(self._call_region.size))
        for box in parent.boxes:
            if box.runtime == self:
                box.pushattrs(
                    callregion=self._call_region.addr)

    def box_parent(self, parent, box):
        # register hooks
        self._load_hook = parent.addimport(
            '__box_%s_load' % box.name, 'fn() -> err',
            scope=parent.name, source=self.__argname__,
            doc="Called to load the box during init. Normally provided "
                "by the loader but can be overriden.")
        self._abort_hook = parent.addimport(
            '__box_%s_abort' % box.name, 'fn(err err) -> noreturn',
            scope=parent.name, source=self.__argname__, weak=True,
            doc="Called when this box aborts, either due to an illegal "
                "memory access or other failure. the error code is "
                "provided as an argument.")
        self._write_hook = parent.addimport(
            '__box_%s_write' % box.name,
            'fn(i32, const u8[size], usize size) -> errsize',
            scope=parent.name, source=self.__argname__, weak=True,
            doc="Override __box_write for this specific box.")
        self._flush_hook = parent.addimport(
            '__box_%s_flush' % box.name,
            'fn(i32) -> err',
            scope=parent.name, source=self.__argname__, weak=True,
            doc="Override __box_flush for this specific box.")
        super().box_parent(parent, box)

    def box(self, box):
        # need isolated stack
        if not box.stack.size:
            print("warning: Box `%s` has no stack!" % box.name)

        # check memory regions against MPU limitations
        for memory in box.memories:
            self._check_mpu_region(memory)

        super().box(box)
        self._jumptable.alloc(box, 'rp')

        # plugs
        self._abort_plug = box.addexport(
            '__box_abort', 'fn(err) -> noreturn',
            scope=box.name, source=self.__argname__, weak=True)
        self._write_plug = box.addexport(
            '__box_write', 'fn(i32, const u8[size], usize size) -> errsize',
            scope=box.name, source=self.__argname__, weak=True)
        self._flush_plug = box.addexport(
            '__box_flush', 'fn(i32) -> err',
            scope=box.name, source=self.__argname__, weak=True)

        # zeroing takes care of bss
        if self._zero:
            box.addexport('__box_bss_init', 'fn() -> void',
                scope=box.name, source=self.__argname__, weak=True)

    def _parentimports(self, parent, box):
        """
        Get imports that need linking.
        Yields import, needswrapper, needsinit.
        """
        # implicit imports
        yield Import(
            '__box_%s_postinit' % box.name,
            'fn(const u32*) -> err32',
            source=self.__argname__), False, False

        # imports that need linking
        for import_ in parent.imports:
            if import_.link and import_.link.export.box == box:
                yield (import_.postbound(),
                    len(import_.boundargs) > 0 or box.init == 'lazy',
                    box.init == 'lazy')

    def _parentexports(self, parent, box):
        """
        Get exports that need linking.
        Yields export, needswrapper.
        """
        # implicit exports
        yield Export(
            '__box_%s_write' % box.name,
            'fn(i32, const u8*, usize) -> errsize',
            source=self.__argname__), False
        yield Export(
            '__box_%s_flush' % box.name,
            'fn(i32) -> err',
            source=self.__argname__), False

        # exports that need linking
        for export in parent.exports:
            if any(link.import_.box == box for link in export.links):
                yield export.prebound(), len(export.boundargs) > 0

    def _imports(self, box):
        """
        Get imports that need linking.
        Yields import, needswrapper.
        """
        # implicit imports
        yield Import(
            '__box_write',
            'fn(i32, const u8[size], usize size) -> errsize',
            source=self.__argname__), False
        yield Export(
            '__box_flush',
            'fn(i32) -> err',
            source=self.__argname__), False

        # imports that need linking
        for import_ in box.imports:
            if import_.link and import_.link.export.box != box:
                yield import_.postbound(), len(import_.boundargs) > 0

    def _exports(self, box):
        """
        Get exports that need linking.
        Yields export, needswrapper
        """
        # implicit exports
        yield Export(
            '__box_init', 'fn() -> err32',
            source=self.__argname__), False

        # exports that need linking
        for export in box.exports:
            if export.scope != box:
                yield export.prebound(), len(export.boundargs) > 0

    def build_mk(self, output, box):
        # target rule
        output.decls.insert(0, '%(name)-16s ?= %(target)s',
            name='TARGET', target=output.get('target', '%(box)s.elf'))

        out = output.rules.append(doc='target rule')
        out.printf('$(TARGET): $(OBJ) $(BOXES) $(ARCHIVES) $(LDSCRIPT)')
        with out.indent():
            out.printf('$(CC) $(OBJ) $(BOXES) $(LDFLAGS) -o $@')

        super().build_mk(output, box)

    def build_parent_c_prologue(self, output, parent):
        super().build_parent_c_prologue(output, parent)

        output.decls.append(MPU_STATE)

        self._build_mpu_impl(output, parent)

        output.decls.append('#define __BOX_COUNT %(boxcount)d',
            boxcount=sum(1 for box in parent.boxes if box.runtime == self))
        output.decls.append(BOX_STATE)

    def build_parent_c(self, output, parent, box):
        super().build_parent_c(output, parent, box)

        out = output.decls.append()
        out.printf('//// %(box)s state ////')
        out.printf('struct __box_state __box_%(box)s_state;')
        out.printf('extern uint32_t __box_%(box)s_jumptable[];')

        self._build_mpu_regions(output, parent, box)

        output.decls.append('//// %(box)s exports ////')
        for import_, needsinit in ((import_, needsinit)
                for import_, needswrapper, needsinit in
                    self._parentimports(parent, box)
                if needswrapper):
            out = output.decls.append(
                fn=output.repr_fn(import_),
                prebound=output.repr_fn(import_,
                    name='__box_import_%(alias)s',
                    attrs=['extern']),
                alias=import_.alias)
            out.printf('%(fn)s {')
            with out.indent():
                # inject lazy-init?
                if needsinit:
                    out.printf('if (!__box_%(box)s_state.initialized) {')
                    with out.indent():
                        out.printf('int err = __box_%(box)s_init();')
                        out.printf('if (err) {')
                        with out.indent():
                            if import_.isfalible():
                                out.printf('return err;')
                            else:
                                out.printf('__box_abort(err);')
                        out.printf('}')
                    out.printf('}')
                    out.printf()
                # jump to real import
                out.printf('%(prebound)s;')
                out.printf('%(return_)s__box_import_%(alias)s(%(args)s);',
                    return_=('return ' if import_.rets else ''),
                    args=', '.join(map(str, import_.argnamesandbounds())))
            out.printf('}')

        output.decls.append('//// %(box)s imports ////')

        # redirect hooks if necessary
        if not self._write_hook.link:
            out = output.decls.append(
                write_hook=self._write_hook.name,
                doc='redirect %(write_hook)s -> __box_write')
            out.printf('#define %(write_hook)s __box_write')

        if not self._flush_hook.link:
            out = output.decls.append(
                flush_hook=self._flush_hook.name,
                doc='redirect %(flush_hook)s -> __box_flush')
            out.printf('#define %(flush_hook)s __box_flush')

        # wrappers?
        for export in (export
                for export, needswrapper in self._parentexports(parent, box)
                if needswrapper):
            out = output.decls.append(
                fn=output.repr_fn(
                    export.postbound(),
                    name='__box_%(box)s_export_%(alias)s'),
                alias=export.alias)
            out.printf('%(fn)s {')
            with out.indent():
                out.printf('%(return_)s%(alias)s(%(args)s);',
                    return_='return ' if import_.rets else '',
                    args=', '.join(map(str, export.argnamesandbounds())))
            out.printf('}')

        # import jumptable
        out = output.decls.append()
        out.printf('const uint32_t __box_%(box)s_sys_jumptable[] = {')
        with out.indent():
            for export, needswrapper in self._parentexports(parent, box):
                out.printf('(uint32_t)%(prefix)s%(alias)s,',
                    prefix='__box_%(box)s_export_' if needswrapper else '',
                    alias=export.alias)
        out.printf('};')

        # init
        output.decls.append('//// %(box)s init ////')
        out = output.decls.append()
        out.printf('int __box_%(box)s_init(void) {')
        with out.indent():
            out.printf('int err;')
            if box.roommates:
                out.printf('// bring down any overlapping boxes')
            for i, roommate in enumerate(box.roommates):
                with out.pushattrs(roommate=roommate.name):
                    out.printf('extern int __box_%(roommate)s_clobber(void);')
                    out.printf('err = __box_%(roommate)s_clobber();')
                    out.printf('if (err) {')
                    with out.indent():
                        out.printf('return err;')
                    out.printf('}')
                    out.printf()
            out.printf('// make sure that the MPU is initialized')
            out.printf('err = __box_mpu_init();')
            out.printf('if (err) {')
            with out.indent():
                out.printf('return err;')
            out.printf('}')
            out.printf()
            out.printf('// prepare the box\'s stack')
            out.printf('// must use PSP, otherwise boxes could '
                'overflow the ISR stack')
            out.printf('__box_%(box)s_state.lr = '
                '0xfffffffd; // TODO determine fp?')
            out.printf('__box_%(box)s_state.sp = '
                '(void*)__box_%(box)s_jumptable[0];')
            out.printf()
            if self._zero:
                out.printf('// zero memory')
                for memory in box.memoryslices:
                    if 'w' in memory.mode:
                        with out.pushattrs(
                                memory=memory.name,
                                memorystart='__box_%(box)s_%(memory)s_start',
                                memoryend='__box_%(box)s_%(memory)s_end'):
                            out.printf('extern uint8_t %(memorystart)s;')
                            out.printf('extern uint8_t %(memoryend)s;')
                            out.printf('memset(&%(memorystart)s, 0, '
                                '&%(memoryend)s - &%(memorystart)s);')
                out.printf()
            out.printf('// load the box if unloaded')
            out.printf('err = __box_%(box)s_load();')
            out.printf('if (err) {')
            with out.indent():
                out.printf('return err;')
            out.printf('}')
            out.printf()
            out.printf('// call box\'s init')
            out.printf('extern int __box_%(box)s_postinit(void);')
            out.printf('err = __box_%(box)s_postinit();')
            out.printf('if (err) {')
            with out.indent():
                out.printf('return err;')
            out.printf('}')
            out.printf()
            out.printf('__box_%(box)s_state.initialized = true;')
            out.printf('return 0;')
        out.printf('}')

        out = output.decls.append()
        out.printf('int __box_%(box)s_clobber(void) {')
        with out.indent():
            out.printf('__box_%(box)s_state.initialized = false;')
            out.printf('return 0;')
        out.printf('}')

        # stack manipulation
        output.includes.append('<assert.h>')
        out = output.decls.append(
            memory=box.stack.memory.name)
        out.printf('void *__box_%(box)s_push(size_t size) {')
        with out.indent():
            out.printf('size = (size+3)/4;')
            out.printf('extern uint8_t __box_%(box)s_%(memory)s_start;')
            out.printf('if (__box_%(box)s_state.sp - size '
                    '< (uint32_t*)&__box_%(box)s_%(memory)s_start) {')
            with out.indent():
                out.printf('return NULL;')
            out.printf('}')
            out.printf()
            out.printf('__box_%(box)s_state.sp -= size;')
            out.printf('return __box_%(box)s_state.sp;')
        out.printf('}')

        out = output.decls.append(
            memory=box.stack.memory.name)
        out.printf('void __box_%(box)s_pop(size_t size) {')
        with out.indent():
            out.printf('size = (size+3)/4;')
            out.printf('__attribute__((unused))')
            out.printf('extern uint8_t __box_%(box)s_%(memory)s_end;')
            out.printf('assert(__box_%(box)s_state.sp + size '
                '<= (uint32_t*)&__box_%(box)s_%(memory)s_end);')
            out.printf('__box_%(box)s_state.sp += size;')
        out.printf('}')

    def build_parent_c_epilogue(self, output, parent):
        super().build_parent_c_epilogue(output, parent)

        # state
        output.decls.append('struct __box_state __box_sys_state;')

        out = output.decls.append()
        out.printf('struct __box_state *const __box_state[__BOX_COUNT+1] = {')
        with out.indent():
            out.printf('&__box_sys_state,')
            for box in parent.boxes:
                if box.runtime == self:
                    out.printf('&__box_%(box)s_state,', box=box.name)
        out.printf('};')

        # abort hooks
        out = output.decls.append()
        out.printf('void (*const __box_aborts[])(int err) = {')
        with out.indent():
            out.printf('NULL,')
            for box in parent.boxes:
                if box.runtime == self:
                    if box.runtime._abort_hook.link:
                        out.printf(box.runtime._abort_hook.link.import_.alias)
                    else:
                        out.printf('NULL,')
        out.printf('};')

        # mpu regions
        self._build_mpu_sysregions(output, parent)

        out = output.decls.append()
        out.printf('const struct __box_mpuregions *const '
            '__box_mpuregions[__BOX_COUNT+1] = {')
        with out.pushindent():
            out.printf('&__box_sys_mpuregions,')
            for box in parent.boxes:
                if box.runtime == self:
                    out.printf('&__box_%(box)s_mpuregions,', box=box.name)
        out.printf('};')

        # jumptables
        out = output.decls.append()
        out.printf('const uint32_t *const '
            '__box_jumptables[__BOX_COUNT] = {')
        with out.pushindent():
            for box in parent.boxes:
                if box.runtime == self:
                    out.printf('__box_%(box)s_jumptable,',
                        box=box.name)
        out.printf('};');

        out = output.decls.append()
        out.printf('const uint32_t *const '
            '__box_sys_jumptables[__BOX_COUNT] = {')
        with out.pushindent():
            for box in parent.boxes:
                if box.runtime == self:
                    out.printf('__box_%(box)s_sys_jumptable,',
                        box=box.name)
        out.printf('};');

        # mpu handlers
        output.decls.append(MPU_HANDLERS)

    def build_parent_ld(self, output, parent, box):
        super().build_parent_ld(output, parent, box)

        output.decls.append('__box_%(box)s_jumptable = '
            '__box_%(box)s_%(memory)s_start;',
            memory=self._jumptable.memory.name,
            doc='box %(box)s jumptable')

    def build_parent_ld_epilogue(self, output, parent):
        super().build_parent_ld_prologue(output, parent)

        out = output.decls.append(doc='call region')
        out.printf('__box_callregion = %(callregion)#0.8x;')
        out.printf('__box_return = __box_callregion;')

        # create box calls for imports
        boxcount = sum(1 for box in parent.boxes if box.runtime == self)
        out = output.decls.append(doc='box calls')
        for i, box in enumerate(box
                for box in parent.boxes
                if box.runtime == self):
            for j, (import_, needswrapper, _) in enumerate(
                    self._parentimports(parent, box)):
                out.printf('%(import_)-24s = __box_callregion + '
                    '4*(2 + %(boxcount)d*%(j)d + %(i)d) + 2*%(falible)d + 1;',
                    import_='__box_import_'+import_.alias
                        if needswrapper else
                        import_.alias,
                    falible=import_.isfalible(),
                    i=i,
                    j=j,
                    boxcount=boxcount)

    def build_c(self, output, box):
        super().build_c(output, box)

        out = output.decls.append()
        out.printf('int __box_init(void) {')
        with out.indent():
            if self.data_init_hook.link:
                out.printf('// data inited by %(hook)s',
                    hook=self.data_init_hook.link.export.source)
                out.printf()
            else:
                out.printf('// load data')
                out.printf('extern uint32_t __data_init_start;')
                out.printf('extern uint32_t __data_start;')
                out.printf('extern uint32_t __data_end;')
                out.printf('const uint32_t *s = &__data_init_start;')
                out.printf('for (uint32_t *d = &__data_start; '
                    'd < &__data_end; d++) {')
                with out.indent():
                    out.printf('*d = *s++;')
                out.printf('}')
                out.printf()
            if self.bss_init_hook.link:
                out.printf('// bss inited by %(hook)s',
                    hook=self.bss_init_hook.link.export.source)
                out.printf()
            else:
                out.printf('// zero bss')
                out.printf('extern uint32_t __bss_start;')
                out.printf('extern uint32_t __bss_end;')
                out.printf('for (uint32_t *d = &__bss_start; '
                    'd < &__bss_end; d++) {')
                with out.indent():
                    out.printf('*d = 0;')
                out.printf('}')
                out.printf()
            out.printf('// init libc')
            out.printf('extern void __libc_init_array(void);')
            out.printf('__libc_init_array();')
            out.printf()
            out.printf('return 0;')
        out.printf('}')

        output.decls.append('//// imports ////')
        for import_ in (import_
                for import_, needswrapper in self._imports(box)
                if needswrapper):
            out = output.decls.append(
                fn=output.repr_fn(import_),
                prebound=output.repr_fn(import_,
                    name='__box_import_%(alias)s',
                    attrs=['extern']),
                alias=import_.alias)
            out.printf('%(fn)s {')
            with out.indent():
                out.printf('%(prebound)s;')
                out.printf('%(return_)s__box_export_%(alias)s(%(args)s);',
                    return_='return ' if import_.rets else '',
                    args=', '.join(map(str, import_.argnamesandbounds())))
            out.printf('}')

        output.decls.append('//// exports ////')
        for export in (export
                for export, needswrapper in self._exports(box)
                if needswrapper):
            out = output.decls.append(
                fn=output.repr_fn(
                    export.postbound(),
                    name='__box_export_%(alias)s'),
                alias=export.alias)
            out.printf('%(fn)s {')
            with out.indent():
                out.printf('%(return_)s%(alias)s(%(args)s);',
                    return_='return ' if import_.rets else '',
                    args=', '.join(map(str, export.argnamesandbounds())))
            out.printf('}')

        out = output.decls.append(doc='box-side jumptable')
        out.printf('extern uint8_t __stack_end;')
        out.printf('__attribute__((used, section(".jumptable")))')
        out.printf('const uint32_t __box_jumptable[] = {')
        with out.pushindent():
            if box.stack.size > 0:
                out.printf('(uint32_t)&__stack_end,')
            for export, needswrapper in self._exports(box):
                out.printf('(uint32_t)%(prefix)s%(alias)s,',
                    prefix='__box_export_' if needswrapper else '',
                    alias=export.alias)
        out.printf('};')

    def build_ld(self, output, box):
        output.decls.append('__box_callregion = %(callregion)#0.8x;')

        # create box calls for imports
        out = output.decls.append(doc='box calls')
        out.printf('%(import_)-24s = __box_callregion + '
            '4*%(i)d + 2*%(falible)d + 1;',
            import_='__box_abort',
            falible=False,
            i=1)
        for i, (import_, needswrapper) in enumerate(self._imports(box)):
            out.printf('%(import_)-24s = __box_callregion + '
                '4*%(i)d + 2*%(falible)d + 1;',
                import_='__box_import_' + import_.alias
                    if needswrapper else
                    import_.alias,
                falible=import_.isfalible(),
                i=2+i)

        if not output.no_sections:
            out = output.sections.append(
                section='.jumptable',
                memory=self._jumptable.memory.name)
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__jumptable_start = .;')
            out.printf('%(section)s . : {')
            with out.pushindent():
                out.printf('__jumptable = .;')
                out.printf('KEEP(*(.jumptable))')
            out.printf('} > %(MEMORY)s')
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__jumptable_end = .;')

        super().build_ld(output, box)

