
from .. import runtimes
from .. import util
from ..box import Fn
import itertools as it

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

MPU_REGISTERS = """
#define SHCSR    ((volatile uint32_t*)0xe000ed24)
#define MPU_TYPE ((volatile uint32_t*)0xe000ed90)
#define MPU_CTRL ((volatile uint32_t*)0xe000ed94)
#define MPU_RBAR ((volatile uint32_t*)0xe000ed9c)
#define MPU_RASR ((volatile uint32_t*)0xe000eda0)
"""

BOX_SYS_DISPATCH = """
uint64_t __box_callsetup(uint32_t lr, uint32_t *sp,
        uint32_t op, uint32_t *fp) {
    // save lr + sp
    const uint32_t *jumptable = __box_jumptables[__box_active];
    uint32_t *state = (uint32_t*)jumptable[0];
    sp[0] = (uint32_t)fp;
    sp[1] = state[-2];
    sp[2] = state[-1];
    state[-2] = (uint32_t)lr;
    state[-1] = (uint32_t)sp;

    // TODO table walk
    uint32_t path = (op & 0xffff)/2;
    uint32_t retbox = __box_active;
    __box_active = path %% BOX_COUNT;
    const uint32_t *targetjumptable = __box_jumptables[__box_active];
    uint32_t *targetstate = (uint32_t*)targetjumptable[0];
    uint32_t targetlr = targetstate[-2];
    uint32_t *targetsp = (uint32_t*)targetstate[-1];
    // don't allow returns while executing
    targetstate[-2] = 0; 
    // need sp to fixup instruction aborts
    targetstate[-1] = (uint32_t)targetsp;
    uint32_t targetpc = targetjumptable[path / BOX_COUNT + 1];

    // setup new call frame
    targetsp -= 8;
    targetsp[0] = fp[0];        // r0 = arg0
    targetsp[1] = fp[1];        // r1 = arg1
    targetsp[2] = fp[2];        // r2 = arg2
    targetsp[3] = fp[3];        // r3 = arg3
    targetsp[4] = fp[4];        // r12 = r12
    targetsp[5] = 0x1ffd0001 + (retbox<<1); // lr = __box_ret
    targetsp[6] = targetpc;     // pc = targetpc
    targetsp[7] = fp[7];        // psr = psr

    return ((uint64_t)targetlr) | ((uint64_t)(uint32_t)targetsp << 32);
}

__attribute__((naked, noreturn))
void __box_call(uint32_t lr, uint32_t *sp, uint32_t op) {
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
        // call into c now that we have stack control
        "bl __box_callsetup \\n\\t"
        // update new sp
        "tst r0, #0x4 \\n\\t"
        "ite eq \\n\\t"
        "msreq msp, r1 \\n\\t"
        "msrne psp, r1 \\n\\t"
        // return to call
        "bx r0 \\n\\t"
    );
}

uint64_t __box_retsetup(uint32_t lr, uint32_t *sp,
        uint32_t op, uint32_t *fp) {
    // save lr + sp
    const uint32_t *jumptable = __box_jumptables[__box_active];
    uint32_t *state = (uint32_t*)jumptable[0];
    // drop exception frame and fixup instruction aborts
    sp = (uint32_t*)state[-1];
    state[-2] = (uint32_t)lr;
    state[-1] = (uint32_t)sp;

    // TODO table walk
    uint32_t path = (op & 0xffff)/2;
    __box_active = path %% BOX_COUNT;
    const uint32_t *targetjumptable = __box_jumptables[__box_active];
    uint32_t *targetstate = (uint32_t*)targetjumptable[0];
    uint32_t targetlr = targetstate[-2];
    uint32_t *targetsp = (uint32_t*)targetstate[-1];
    uint32_t *targetfp = (uint32_t*)targetsp[0];
    targetstate[-2] = targetsp[1];
    targetstate[-1] = targetsp[2];

    // copy return frame
    targetfp[0] = fp[0];       // r0 = arg0
    targetfp[1] = fp[1];       // r1 = arg1
    targetfp[2] = fp[2];       // r2 = arg2
    targetfp[3] = fp[3];       // r3 = arg3
    targetfp[6] = targetfp[5]; // pc = lr

    return ((uint64_t)targetlr) | ((uint64_t)(uint32_t)targetsp << 32);
}

__attribute__((naked, noreturn))
void __box_ret(uint32_t lr, uint32_t *sp, uint32_t op) {
    __asm__ volatile (
        // keep track of rets
        "mov r3, r1 \\n\\t"
        // drop exception frame
        //"add r1, r1, #8*4 \\n\\t"
        //"add r1, r1, #9*4 \\n\\t"
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

void __box_halt(uint32_t lr, uint32_t *sp, uint32_t op) {
    printf("Intercepted fault\\n");
    printf("CFSR 0x%%08x\\n", *(volatile uint32_t*)0xe000ed28);
    printf("isr lr 0x%%08x\\n", lr);
    uint32_t pc = sp[6];
    printf("pc 0x%%08x\\n", pc);
    printf("sp 0x%%08x\\n", sp);
    printf("op 0x%%08x\\n", op);
    while (1) {}
}

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
        "ldr r3, =#0x1ffc0000 \\n\\t"
        "sub r3, r2, r3 \\n\\t"
        "lsrs r3, r3, #16 \\n\\t"
        "beq __box_call \\n\\t"
        // ret?
        "ldr r3, =#0x1ffd0000 \\n\\t"
        "sub r3, r2, r3 \\n\\t"
        "lsrs r3, r3, #16 \\n\\t"
        "beq __box_ret \\n\\t" // TODO box ret
        // fallback to fault handler (call 1)
        // TODO this
        "b __box_halt \\n\\t"
    );
}
"""

BOX_SYS_INIT = """
extern int32_t __box_%(box)s_rawinit(void);
int32_t __box_%(box)s_init(void) {
    // make sure MPU is initialized
    if (!(*MPU_CTRL & 0x1)) {
        // do we have an MPU?
        assert(*MPU_TYPE);
        // enable MemManage exception
        *SHCSR = *SHCSR | 0x00010000;
        // setup call region
        *MPU_RBAR = 0x1ffc0000 | 0x10;
        // disallow execution
        *MPU_RASR = 0x10230021;
        // enable the MPU
        *MPU_CTRL = *MPU_CTRL | 0x5;

    }

    // prepare box's stack
    uint32_t *state = (uint32_t*)__box_%(box)s_jumptable[0];
    state[-2] = 0xfffffff9; // TODO determine fp?
    state[-1] = (uint32_t)(state - 2);

    // call box's init
    return __box_%(box)s_rawinit();
}
"""

@runtimes.runtime
class ARMv7MPURuntime(runtimes.Runtime):
    """
    A bento-box runtime that uses a v7 MPU to provide memory isolation
    between boxes.
    """
    __argname__ = "armv7_mpu_"
    __arghelp__ = __doc__
#
#    # TODO dupe to Runtime
#    def box(self, box):
#        self.box = box

#    def build_common_header_glue_(self, output):
#        output.includes.append("<sys/types.h>")
#        output.decls.append('void __box_%(box)s_init(void);',
#            doc='jumptable initialization')

    def __init__(self):
        super().__init__()
        self.ids = {}

    def box(self, box):
        super().box(box)
        # TODO provide this automatically?
        # we're running this multiple times, which technically works...
        parent = box.getparent()

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

    def build_common_c_glue_(self, output, box):
        output.decls.append('//// jumptable declarations ////')

        outf = output.decls.append()
        outf.writef('struct %(box)s_exportjumptable {\n')
        with outf.pushindent():
            # special entries for the sp and __box_init
            outf.writef('uint32_t *__box_%(box)s_stack_end;\n')
            outf.writef('void (*__box_%(box)s_init)(void);\n')
            for export in box.exports:
                outf.writef('%(fn)s;\n', fn=export.repr_c_ptr())
        outf.writef('};\n')

        outf = output.decls.append()
        outf.writef('struct %(box)s_importjumptable {\n')
        with outf.pushindent():
            # special entries for __box_write and __box_fault
            outf.writef('void (*__box_%(box)s_fault)(void);\n')
            outf.writef('int (*__box_%(box)s_write)('
                'int a, char* b, int c);\n') # TODO are these the correct types??
            for import_ in box.imports:
                outf.writef('%(fn)s;\n', fn=import_.repr_c_ptr())
        outf.writef('};\n')

    def build_parent_prologue_c_glue_(self, output, sys):
        output.decls.append('//// jumptable implementation ////')
        #output.includes.append('"fsl_sysmpu.h"')
        output.decls.append(
            'extern int _write(int handle, char *buffer, int size);',
            doc='GCC stdlib hook')

        output.decls.append(MPU_REGISTERS)

        outf = output.decls.append(doc='System state')
        outf.writef('uint32_t __box_active = 0;\n')
        outf.writef('uint32_t __box_sys_state[2];\n')

        outf = output.decls.append()
        outf.writef('const uint32_t __box_sys_jumptable[] = {\n')
        with outf.pushindent():
            outf.writef('(uint32_t)(&__box_sys_state + 1),\n')
            outf.writef('(uint32_t)&_write,\n')
            for export in sys.exports:
                outf.writef('(uint32_t)%(export)s,\n', export=export.name)
        outf.write('};')

        outf = output.decls.append()
        for box in sys.boxes:
            if box.runtime.name == self.__argname__:
                outf.writef(
                    'extern const uint32_t __box_%(box)s_jumptable[];\n',
                    box=box.name)

        outf = output.decls.append()
        outf.writef('#define BOX_COUNT (sizeof(__box_jumptables)/'
            'sizeof(__box_jumptables[0]))\n')
        outf.write('const uint32_t *__box_jumptables[] = {\n');
        with outf.pushindent():
            outf.writef('__box_sys_jumptable,\n')
            for box in sys.boxes:
                if box.runtime.name == self.__argname__:
                    outf.writef('__box_%(box)s_jumptable,\n',
                        box=box.name)
        outf.write('};');
        
        output.includes.append('<assert.h>') # TODO need this?
        output.decls.append(BOX_SYS_DISPATCH)

    def build_parent_c_glue_(self, output, sys, box):
        output.decls.append(BOX_SYS_INIT)
#
#    def build_parent_c_glue_(self, output, sys, box):
#        self.build_common_c_glue_(output, box)
#
#        outf = output.decls.append(doc='system-side jumptable')
#        outf.writef('const struct %(box)s_importjumptable '
#            '__%(box)s_importjumptable = {\n')
#        with outf.pushindent():
#            # special entries for __box_fault and __box_write
#            outf.writef('__box_%(box)s_fault,\n')
#            outf.writef('_write,\n')
#            for import_ in box.imports:
#                outf.writef('%(import_)s,\n', import_=import_.name)
#        outf.writef('};\n')

    def build_c_glue_(self, output, box):
        self.build_common_c_glue_(output, box)

        output.decls.append('//// jumptable implementation ////')
        output.decls.append(BOX_INIT)
        output.decls.append(BOX_WRITE)

        output.decls.append('extern uint32_t __stack_end;')
        outf = output.decls.append(doc='box-side jumptable')
        outf.writef('__attribute__((section(".jumptable")))\n')
        outf.writef('__attribute__((used))\n')
        outf.writef('const struct %(box)s_exportjumptable '
            '__box_%(box)s_jumptable = {\n')
        with outf.pushindent():
            # special entries for the sp and __box_init
            outf.writef('&__stack_end,\n')
            outf.writef('__box_%(box)s_init,\n')
            for export in box.exports:
                outf.writef('%(export)s,\n', export=export.name)
        outf.writef('};\n')

    def build_parent_partial_ldscript_(self, output, sys, box):
        # create box calls for imports
        output.decls.append('/* box calls */')
        for import_ in it.chain(
                # TODO rename this
                ['__box_%(box)s_rawinit'],
                (import_.name for import_ in box.exports)):
            output.decls.append('%(import_)-24s = 0x1ffc0001 + %(id)d*2;',
                import_=import_,
                id=self.ids[import_ % dict(box=box.name)])
        output.decls.append()

#        # create inherited symbols?
#        with output.pushattrs(
#                section_prefix='.box.%(box)s.',
#                symbol_prefix='__box_%(box)s_',
#                memory_prefix='box_%(box)s_'):
#            self.build_box_ldscript_(box, output)

        # TODO there has to be a better way to do this
        # TODO so many issues, decide best memory elsewhere? (box)
        # insert valid?
        # should we do all boxing work here?
        # allow default in linkerscript?
        # allow symbol injection?
        # ugh
#        memory = box.bestmemory('rx', box.jumptable.size,
#            consumed=output.consumed)
        memory, _, _ = box.consume('rx', box.jumptable.size)
        outf = output.sections.insert(0,
            box_memory=memory.name,
            section='.box.%(box)s.%(box_memory)s',
            memory='box_%(box)s_%(box_memory)s')
        outf.writef('. = ORIGIN(%(MEMORY)s);\n')
        outf.writef('__box_%(box)s_jumptable = .;')
        super().build_parent_partial_ldscript_(output, sys, box)

    def build_parent_ldscript_(self, output, sys, box):
        return self.build_parent_partial_ldscript_(output, sys, box)

    def build_partial_ldscript_(self, output, box):
        if output['section_prefix'] == '.':
            # create box calls for imports
            output.decls.append('/* box calls */')
            for i, import_ in enumerate(it.chain(
                    ['__box_write'],
                    (import_.name for import_ in box.imports))):
                output.decls.append('%(import_)-24s = 0x1ffc0001 + %(id)d*2;',
                    import_=import_,
                    id=self.ids[import_])
            output.decls.append()

    def build_ldscript_(self, output, box):
        self.build_partial_ldscript_(output, box)
        
        # TODO handle this in ldscript class? ldscript.consume?
        # TODO make jumptable come before ldscript declarations.
        # Need box method?
        # TODO what... this just doesn't work...
#        memory = box.bestmemory('rx', box.jumptable.size,
#            consumed=output.consumed)
        memory, _, _ = box.consume('rx', box.jumptable.size)
        #print(output.consumed)
        # TODO hm
        #output.consumed[memory.name] += box.jumptable.size
        outf = output.sections.insert(0,
            section='%(section_prefix)s' + 'jumptable',
            memory='%(memory_prefix)s' + memory.name)
            # TODO move these?
            # TODO shortcut for capitalized?
#            prefixed_section='%(section_prefix)s%(section)s',
#            prefixed_memory='%(memory_prefix)s%(memory)s',
#            prefixed_symbol='%(symbol_prefix)s%(symbol)s', symbol='')
        outf.writef('%(section)s : {\n')
        with outf.pushindent():
            outf.writef('. = ALIGN(%(align)d);\n')
            outf.writef('%(symbol_prefix)sjumptable = .;\n')
            outf.writef('KEEP(*(%(section_prefix)sjumptable))\n')
            outf.writef('. = ALIGN(%(align)d);\n')
            outf.writef('%(symbol_prefix)sjumptable_end = .;\n')
        outf.writef('} > %(MEMORY)s')

        super().build_ldscript_(output, box)

#    def build(self):
#        self.box.parentbuild('c_glue_', self.build_sys_c_glue_)
#        self.box.build('c_glue_', self.build_box_c_glue_)
#        self.box.parentbuild('ldscript_', self.build_sys_ldscript_)
#        self.box.build('ldscript_', self.build_box_ldscript_)
#        self.box.parentbuild('partial_ldscript_', self.build_sys_ldscript_)
#        self.box.build('partial_ldscript_', self.build_box_partial_ldscript_)
#
#        if 'c_glue_' in self.box.outputs:
#            self.build_box_c_glue_(self.box, self.box.outputs['c_glue_'])
#        if self.box.parent and 'c_glue_' in self.box.parent.outputs:
#            with self.box.parent.outputs['c_glue_'].pushattrs(
#                    box=self.box.name) as output:
#                self.build_sys_c_glue_(self.box.parent, self.box, output)
#        for ldscript in ['ldscript_', 'partial_ldscript_']:
#            if ldscript in self.box.outputs:
#                self.build_box_ldscript_(self.box, self.box.outputs[ldscript],
#                    partial='partial' in ldscript) # TODO hm
#            if self.box.parent and ldscript in self.box.parent.outputs:
#                with self.box.parent.outputs[ldscript].pushattrs(
#                        box=self.box.name) as output:
#                    self.build_sys_ldscript_(self.box.parent, self.box, output)
#
##        if 'header_glue_' in self.box.outputs:
##            self.build_common_header_glue_(self.box.outputs['header_glue_'])
        

    def build_common_header_glue_(self, output, sys, box):
        output.append_include("<sys/types.h>")

        # TODO error if import not found?
        output.append_decl('// exports from box %s' % box.name)
        for export in box.exports:
            output.append_decl('extern %(fn)s;', fn=export.repr_c())
#            assert len(export.rets) <= 1
#            output.append_decl('extern %(ret)s %(export)s(%(args)s);',
#                export=export.name,
#                args='void' if not export.args else ', '.join(
#                    arg.repr_c(name) for arg, name in zip(
#                        export.args, util.arbitrary())),
#                ret='void' if not export.rets else export.rets[0].repr_c())
        output.append_decl('')

        outf = output.append_decl()
        outf.writef('struct %(box)s_exportjumptable {\n')
        # special entries for the sp and __box_init
        outf.writef('    uint32_t *__box_%(box)s_stack_end;\n')
        outf.writef('    void (*__box_%(box)s_init)(void);\n')
        for export in box.exports:
            outf.writef('    %(fn)s;\n', fn=export.repr_c_ptr())
#            outf.writef('    %(ret)s (*%(export)s)(%(args)s);\n',
#                export=export.name,
#                args='void' if not export.args else ', '.join(
#                    arg.repr_c(name) for arg, name in zip(
#                        export.args, util.arbitrary())),
#                ret='void' if not export.rets else export.rets[0].repr_c())
        outf.writef('};\n')

        # TODO error if import not found?
        output.append_decl('// imports from box %s' % box.name)
        for import_ in box.imports:
            output.append_decl('extern %(fn)s;', fn=import_.repr_c())
#            assert len(import_.rets) <= 1
#            output.append_decl('extern %(ret)s %(import_)s(%(args)s);',
#                import_=import_.name,
#                args='void' if not import_.args else ', '.join(
#                    arg.repr_c(name) for arg, name in zip(
#                        import_.args, util.arbitrary())),
#                ret='void' if not import_.rets else import_.rets[0].repr_c())
        output.append_decl('')

        outf = output.append_decl()
        outf.writef('struct %(box)s_importjumptable {\n')
        # special entries for __box_write and __box_fault
        outf.writef('    void (*__box_%(box)s_fault)(void);\n')
        outf.writef('    int (*__box_%(box)s_write)('
            'int a, char* b, int c);\n')
        for import_ in box.imports:
            outf.writef('    %(fn)s;\n', fn=import_.repr_c_ptr())
#            outf.writef('    %(ret)s (*%(import_)s)(%(args)s);\n',
#                import_=import_.name,
#                args='void' if not import_.args else ', '.join(
#                    arg.repr_c(name) for arg, name in zip(
#                        import_.args, util.arbitrary())),
#                ret='void' if not import_.rets else import_.rets[0].repr_c())
        outf.writef('};\n')

#    def build_common_header_(self, outf, sys, box):
#        outf.writef('// exports from box %s\n' % box.name)
#        # TODO error if import not found?
#        for export in box.exports.values():
#            assert len(export.rets) <= 1
#            outf.writef('extern %(ret)s %(name)s(%(args)s);\n' % dict(
#                name=export.name,
#                args='void' if not export.args else ', '.join(
#                    '%s %s' % arg for arg in zip(
#                        export.args, util.arbitrary())),
#                ret='void' if not export.rets else export.rets[0]))
#        outf.writef('\n')
#        outf.writef('struct %s_exportjumptable {\n' % box.name)
#        # special entries for the sp and __box_init
#        outf.writef('    uint32_t *__box_%s_stack_end;\n' % box.name)
#        outf.writef('    void (*__box_%s_init)(void);\n' % box.name)
#        for export in box.exports.values():
#            outf.writef('    %(ret)s (*%(name)s)(%(args)s);\n' % dict(
#                name=export.name,
#                args='void' if not export.args else ', '.join(
#                    '%s %s' % arg for arg in zip(
#                        export.args, util.arbitrary())),
#                ret='void' if not export.rets else export.rets[0]))
#        outf.writef('};\n')
#        outf.writef('\n')
#
#        outf.writef('// imports from box %s\n' % box.name)
#        # TODO error if import not found?
#        for import_ in box.imports.values():
#            assert len(import_.rets) <= 1
#            outf.writef('extern %(ret)s %(name)s(%(args)s);\n' % dict(
#                name=import_.name,
#                args='void' if not import_.args else ', '.join(
#                    '%s %s' % arg for arg in zip(
#                        import_.args, util.arbitrary())),
#                ret='void' if not import_.rets else import_.rets[0]))
#        outf.writef('\n')
#        outf.writef('struct %s_importjumptable {\n' % box.name)
#        # special entries for __box_write and __box_fault
#        outf.writef('    void (*__box_%s_write)('
#            'int a, char* b, int c);\n' % box.name)
#        outf.writef('    void (*__box_%s_fault)(void);\n' % box.name)
#        for import_ in box.imports.values():
#            outf.writef('    %(ret)s (*%(name)s)(%(args)s);\n' % dict(
#                name=import_.name,
#                args='void' if not import_.args else ', '.join(
#                    '%s %s' % arg for arg in zip(
#                        import_.args, util.arbitrary())),
#                ret='void' if not import_.rets else import_.rets[0]))
#        outf.writef('};\n')
#        outf.writef('\n')

    def build_sys_header_glue_(self, sys, box, output):
        """Build system header"""
        output.includes.append("<sys/types.h>")

#        outf = output.decls.append()
#        outf.writef('// jumptable initialization\n')
#        outf.writef('void __box_%(box)s_init(void);\n')
#        output.decls.append(fn=Fn(
#            '__box_%(box)s_init', 'fn() -> void',
#            doc='jumptable initialization'))
        output.decls.append('int32_t __box_%(box)s_init(void);',
            doc='jumptable initialization')

        #self.build_common_header_glue(sys, box, output)

    def build_common_header_glue(self, sys, box, output):
        output.append_include("<sys/types.h>")

        # TODO error if import not found?
        output.append_decl('// exports from box %s' % box.name)
        for export in box.exports:
            output.append_decl('extern %(fn)s;', fn=export.repr_c())
#            assert len(export.rets) <= 1
#            output.append_decl('extern %(ret)s %(export)s(%(args)s);',
#                export=export.name,
#                args='void' if not export.args else ', '.join(
#                    arg.repr_c(name) for arg, name in zip(
#                        export.args, util.arbitrary())),
#                ret='void' if not export.rets else export.rets[0].repr_c())
        output.append_decl('')

        outf = output.append_decl()
        outf.writef('struct %(box)s_exportjumptable {\n')
        # special entries for the sp and __box_init
        outf.writef('    uint32_t *__box_%(box)s_stack_end;\n')
        outf.writef('    void (*__box_%(box)s_init)(void);\n')
        for export in box.exports:
            outf.writef('    %(fn)s;\n', fn=export.repr_c_ptr())
#            outf.writef('    %(ret)s (*%(export)s)(%(args)s);\n',
#                export=export.name,
#                args='void' if not export.args else ', '.join(
#                    arg.repr_c(name) for arg, name in zip(
#                        export.args, util.arbitrary())),
#                ret='void' if not export.rets else export.rets[0].repr_c())
        outf.writef('};\n')

        # TODO error if import not found?
        output.append_decl('// imports from box %s' % box.name)
        for import_ in box.imports:
            output.append_decl('extern %(fn)s;', fn=import_.repr_c())
#            assert len(import_.rets) <= 1
#            output.append_decl('extern %(ret)s %(import_)s(%(args)s);',
#                import_=import_.name,
#                args='void' if not import_.args else ', '.join(
#                    arg.repr_c(name) for arg, name in zip(
#                        import_.args, util.arbitrary())),
#                ret='void' if not import_.rets else import_.rets[0].repr_c())
        output.append_decl('')

        outf = output.append_decl()
        outf.writef('struct %(box)s_importjumptable {\n')
        # special entries for __box_write and __box_fault
        outf.writef('    void (*__box_%(box)s_fault)(void);\n')
        outf.writef('    int (*__box_%(box)s_write)('
            'int a, char* b, int c);\n')
        for import_ in box.imports:
            outf.writef('    %(fn)s;\n', fn=import_.repr_c_ptr())
#            outf.writef('    %(ret)s (*%(import_)s)(%(args)s);\n',
#                import_=import_.name,
#                args='void' if not import_.args else ', '.join(
#                    arg.repr_c(name) for arg, name in zip(
#                        import_.args, util.arbitrary())),
#                ret='void' if not import_.rets else import_.rets[0].repr_c())
        outf.writef('};\n')

#    def build_common_header_(self, outf, sys, box):
#        outf.writef('// exports from box %s\n' % box.name)
#        # TODO error if import not found?
#        for export in box.exports.values():
#            assert len(export.rets) <= 1
#            outf.writef('extern %(ret)s %(name)s(%(args)s);\n' % dict(
#                name=export.name,
#                args='void' if not export.args else ', '.join(
#                    '%s %s' % arg for arg in zip(
#                        export.args, util.arbitrary())),
#                ret='void' if not export.rets else export.rets[0]))
#        outf.writef('\n')
#        outf.writef('struct %s_exportjumptable {\n' % box.name)
#        # special entries for the sp and __box_init
#        outf.writef('    uint32_t *__box_%s_stack_end;\n' % box.name)
#        outf.writef('    void (*__box_%s_init)(void);\n' % box.name)
#        for export in box.exports.values():
#            outf.writef('    %(ret)s (*%(name)s)(%(args)s);\n' % dict(
#                name=export.name,
#                args='void' if not export.args else ', '.join(
#                    '%s %s' % arg for arg in zip(
#                        export.args, util.arbitrary())),
#                ret='void' if not export.rets else export.rets[0]))
#        outf.writef('};\n')
#        outf.writef('\n')
#
#        outf.writef('// imports from box %s\n' % box.name)
#        # TODO error if import not found?
#        for import_ in box.imports.values():
#            assert len(import_.rets) <= 1
#            outf.writef('extern %(ret)s %(name)s(%(args)s);\n' % dict(
#                name=import_.name,
#                args='void' if not import_.args else ', '.join(
#                    '%s %s' % arg for arg in zip(
#                        import_.args, util.arbitrary())),
#                ret='void' if not import_.rets else import_.rets[0]))
#        outf.writef('\n')
#        outf.writef('struct %s_importjumptable {\n' % box.name)
#        # special entries for __box_write and __box_fault
#        outf.writef('    void (*__box_%s_write)('
#            'int a, char* b, int c);\n' % box.name)
#        outf.writef('    void (*__box_%s_fault)(void);\n' % box.name)
#        for import_ in box.imports.values():
#            outf.writef('    %(ret)s (*%(name)s)(%(args)s);\n' % dict(
#                name=import_.name,
#                args='void' if not import_.args else ', '.join(
#                    '%s %s' % arg for arg in zip(
#                        import_.args, util.arbitrary())),
#                ret='void' if not import_.rets else import_.rets[0]))
#        outf.writef('};\n')
#        outf.writef('\n')

    def build_sys_header_glue(self, sys, box, output):
        """Build system header"""
        output.append_include("<sys/types.h>")

        outf = output.append_decl()
        outf.writef('// jumptable initialization\n')
        outf.writef('void __box_%(box)s_init(void);\n')

        self.build_common_header_glue(sys, box, output)

#    def build_sys_header_(self, outf, sys, box):
#        """Build system header for a given box into the given file."""
#        outf.writef('////// AUTOGENERATED //////\n')
#        outf.writef('#ifndef %s_JUMPTABLE_H\n' % box.name.upper())
#        outf.writef('#define %s_JUMPTABLE_H\n' % box.name.upper())
#        outf.writef('\n')
#        outf.writef('#include <sys/types.h>\n') # this should be consolidated
#        outf.writef('\n')
#
#        outf.writef('// jumptable initialization\n')
#        outf.writef('void __box_%s_init(void);\n' % box.name)
#        outf.writef('\n')
#
#        self.build_common_header_(outf, sys, box)
#
#        outf.writef('#endif\n')
#        outf.writef('\n')

    def build_sys_c_glue_prologue(self, sys, output):
        outf = output.append_decl()
        outf.writef('// GCC stdlib hook\n')
        outf.writef('extern int _write(int handle, char *buffer, int size);\n')

    def build_sys_c_glue(self, sys, box, output):
        self.build_common_header_glue(sys, box, output)
        output.append_include('"fsl_sysmpu.h"')

        # TODO should this be split?
        output.append_decl(BOX_SYS_MECH.lstrip())

        outf = output.append_decl()
        outf.writef('// system-side jumptable\n')
        outf.writef('const struct %(box)s_importjumptable '
            '__%(box)s_importjumptable = {\n')
        # special entries for __box_fault and __box_write
        outf.writef('    __box_%(box)s_fault,\n')
        outf.writef('    _write,\n')
        for import_ in box.imports:
            outf.writef('    %(import_)s,\n', import_=import_.name)
        outf.writef('};\n')

#    def build_sys_jumptable_(self, outf, sys, box):
#        """Build system jumptable for a given box into the given file."""
#        # we don't know if user requested header generation, so we just
#        # duplicate it here
#        # TODO need this?
#        self.build_sys_header_(outf, sys, box)
#
#        outf.writef('// GCC stdlib hook\n')
#        outf.writef('extern int _write(int handle, char *buffer, int size);\n')
#        outf.writef('\n')
#
#        outf.writef(BOX_SYS_MECH.strip() % dict(name=box.name))
#        outf.writef('\n')
#        outf.writef('\n')
#
#        outf.writef('// system-side jumptable\n')
#        outf.writef('const struct %(name)s_importjumptable '
#            '__%(name)s_importjumptable = {' % dict(name=box.name))
#        # special entries for __box_fault and __box_write
#        outf.writef('    __box_fault,\n')
#        outf.writef('    _write,\n')
#        for import_ in box.imports.values():
#            outf.writef('    %s,\n' % import_.name)
#        outf.writef('};\n')
#        outf.writef('\n')

#    def build_sys_ldscript_(self, outf, sys, box):
#        """Build system ldscript for a given box into the given file."""

    def build_box_header_glue(self, sys, box, output):
        self.build_common_header_glue(sys, box, output)

#    def build_box_header_(self, outf, sys, box):
#        """Build system header for a given box into the given file."""
#        outf.writef('////// AUTOGENERATED //////\n')
#        outf.writef('#ifndef %s_JUMPTABLE_H\n' % box.name.upper())
#        outf.writef('#define %s_JUMPTABLE_H\n' % box.name.upper())
#        outf.writef('\n')
#        outf.writef('#include <sys/types.h>\n') # this should be consolidated
#        outf.writef('\n')
#
#        self.build_common_header_(outf, sys, box)
#
#        outf.writef('#endif\n')
#        outf.writef('\n')

    def build_box_c_glue(self, sys, box, output):
        self.build_common_header_glue(sys, box, output)

        output.append_decl(BOX_INIT.lstrip())
        output.append_decl(BOX_WRITE.lstrip())

        output.append_decl('extern uint32_t __stack_end;')
        outf = output.append_decl()
        outf.writef('__attribute__((section(".jumptable")))\n')
        outf.writef('__attribute__((used))\n')
        outf.writef('const struct %(box)s_exportjumptable '
            '__box_%(box)s_jumptable = {\n')
        # special entries for the sp and __box_init
        outf.writef('    &__stack_end,\n')
        outf.writef('    __box_%(box)s_init,\n')
        for export in box.exports:
            outf.writef('    %(export)s,\n', export=export.name)
        outf.writef('};\n')

#    def build_box_jumptable_(self, outf, sys, box):
#        """Build system jumptable for a given box into the given file."""
#        # we don't know if user requested header generation, so we just
#        # duplicate it here
#        # TODO need this?
#        self.build_box_header_(outf, sys, box)
#
#        outf.writef(BOX_INIT.strip() % dict(name=box.name))
#        outf.writef('\n')
#        outf.writef('\n')
#
#        outf.writef('extern uint32_t __box_%s_sp;\n' % box.name)
#        outf.writef('__attribute__((section(".jumptable")))\n')
#        outf.writef('__attribute__((used))\n')
#        outf.writef('const struct %(name)s_exportjumptable '
#            '__%(name)s_exportjumptable = {' % dict(name=box.name))
#        # special entries for the sp and __box_init
#        outf.writef('    &__stack_end,\n')
#        outf.writef('    __box_%s_init,\n' % box.name)
#        for export in box.exports.values():
#            outf.writef('    %s,\n' % export.name)
#        outf.writef('};\n')
#        outf.writef('\n')
#
#        # writef handler
#        outf.writef(BOX_WRITE.strip() % dict(name=box.name))
#        outf.writef('\n')
#        outf.writef('\n')

#    def build_box_ldscript_(self, outf, sys, box):
#        """Build system ldscript for a given box into the given file."""
#        outf.writef('\n')
#
#        # TODO make heap optional?
#        outf.writef('HEAP_MIN = '
#            'DEFINED(__heap_min__) ? __heap_min__ : 0x1000;\n')
#        outf.writef('\n')
#
#        outf.writef('MEMORY {\n')
#        for memory in box.memories.values():
#            outf.writef('    mem_%(name)-16s (%(mode)s) : '
#                'ORIGIN = %(start)#010x, LENGTH = %(size)#010x\n' % dict(
#                    name=memory.name,
#                    mode=''.join(c.upper() for c in memory.mode),
#                    start=memory.start,
#                    size=memory.size))
#        outf.writef('}\n')

    def build_sys_partial_ldscript(self, sys, box, output):
        # TODO this should increment...
        # create box calls for exports
        output.append_decl('/* box calls */')
        for i, export in enumerate(it.chain(
                ['__box_%s_boxinit' % box.name],
                (export.name for export in box.exports))):
            output.append_decl('%(export)-16s = 0x0fffc000 + %(i)d*2;',
                export=export,
                i=i)
        output.append_decl()

        # TODO deduplicate this and the box's ldscript...
        # extra decls?
        for section in []: #box.sections.values():
            if section.size is not None:
                output.append_decl('%(section_min)-16s = %(size)#010x;',
                    section_min='__box_%s_%s_min' % (box.name, section.name),
                    size=section.size)

        # create memories
        for memory in box.memories:
            output.append_memory('%(name)-16s (%(mode)s) : '
                'ORIGIN = %(origin)#010x, '
                'LENGTH = %(length)#010x',
                    name='BOX_%s_%s' % (box.name.upper(), memory.name.upper()),
                    mode=''.join(c.upper() for c in sorted(memory.mode)),
                    origin=memory.addr,
                    length=memory.size)

        # create sections
        for name in ['text', 'data', 'bss'] + sorted(
                name for name in [] # box.sections
                if name not in {'text', 'bss', 'data', 'heap', 'stack'}):
            section = None #box.sections.get(name)
            align = (section.align if section else 4) or 4
            # TODO generalize?
            if name in {'text'}:
                bestmemory = box.bestmemory('rx')
            elif name in {'data', 'bss'}:
                bestmemory = box.bestmemory('rw')
#            bestmemory = None
#            for memory in box.memories.values():
#                if memory.sections is not None and name in memory.sections:
#                    bestmemory = memory
#                    break
#            else:
#                if name in {'text'}:
#                    bestmemory = (sorted(
#                        [m for m in box.memories.values()
#                        if set('rx').issubset(m.mode)],
#                        key=lambda m: ('w' in m.mode)*(2<<32) - m.size)
#                            +[None])[0]
#                elif name in {'data', 'bss'}:
#                    bestmemory = (sorted(
#                        [m for m in box.memories.values()
#                        if set('rw').issubset(m.mode)],
#                        key=lambda m: -m.size)
#                            +[None])[0]

            outf = output.append_section()
            outf.writef(
                '.box.%(box)s.%(name)s%(type)s :%(at)s {\n'
                +4*' '+'. = ALIGN(%(align)d);\n'
                +4*' '+'__box_%(box)s_%(name)s = .;\n',
                name=name,
                type=' (NOLOAD)' if name == 'bss' else '',
                at=' AT(__box_%s_data_init)' % box.name
                    if name == 'data' else '',
                align=align)
            if name == 'text':
                outf.writef(4*' '+'__box_%(box)s_jumptable = .;\n')
                outf.writef(4*' '+'__%(box)s_exportjumptable = .;\n') # TODO rename me
                #outf.writef(4*' '+'KEEP(*(.box.%s.jumptable))\n' % box.name)
            outf.writef(''
                +4*' '+'KEEP(*(.box.%(box)s.%(name)s*))\n'
                +4*' '+'. = ALIGN(%(align)d);\n'
                +4*' '+'__box_%(box)s_%(name)s_end = .;\n',
                name=name,
                align=align)
#            if name == 'text':
#                outf.writef(4*' '+'KEEP(*(.box.%s.rodata*))\n' % box.name)
#                outf.writef(4*' '+'KEEP(*(.box.%s.init))\n' % box.name) # TODO can these be wildcarded?
#                outf.writef(4*' '+'KEEP(*(.box.%s.fini))\n' % box.name)
#            elif name == 'bss':
#                pass
#                #outf.writef(4*' '+'*(COMMON)\n') # TODO need this?
            if name == 'text':
                outf.writef(4*' '+'__box_%(box)s_data_init = .;\n')
            outf.writef(
                '} > BOX_%(BOX)s_%(MEM)s\n',
                MEM=bestmemory.name.upper() if bestmemory else '?')

        # here we handle heap/stack separately, they're a bit special since
        # the heap/stack can "share" memory
#        heapsection = box.sections.get('heap')
#        heapalign = (heapsection.align if heapsection else 8) or 8
#        heapsize = heapsection.size
#        stacksection = box.sections.get('stack')
#        stackalign = (stacksection.align if stacksection else 8) or 8
#        stacksize = stacksection.size
        heapalign = 8 # (heapsection.align if heapsection else 8) or 8
        heapsize = box.heap.size
        stackalign = 8 # (stacksection.align if stacksection else 8) or 8
        stacksize = box.stack.size
        bestmemory = box.bestmemory('rw', heapsize+stacksize)
#        bestmemory = None
#        for memory in box.memories.values():
#            if memory.sections is not None and 'heap' in memory.sections:
#                bestmemory = memory
#        else:
#            bestmemory = (sorted(
#                [m for m in box.memories.values()
#                if set('rw').issubset(m.mode)],
#                key=lambda m: -m.size)
#                    +[None])[0]

        outf = output.append_section()
        outf.writef(
            '.box.%(box)s.heap (NOLOAD) : {\n'
            +4*' '+'. = ALIGN(%(align)d);\n'
            +4*' '+'__box_%(box)s_heap = .;\n'
            +4*' '+'__box_%(box)s_stack = .;\n'
            # TODO do we need _all_ of these?
            +4*' '+'__box_%(box)s_heap_end = ('
                'ORIGIN(BOX_%(BOX)s_%(MEM)s) '
                '+ LENGTH(BOX_%(BOX)s_%(MEM)s));\n'
            +4*' '+'__box_%(box)s_stack_end = ('
                'ORIGIN(BOX_%(BOX)s_%(MEM)s) '
                '+ LENGTH(BOX_%(BOX)s_%(MEM)s));\n'
            '} > BOX_%(BOX)s_%(MEM)s',
            align=heapalign,
            MEM=bestmemory.name.upper() if bestmemory else '?')
# TODO reenable this assert
#        if heapsize or stacksize:
#            outf.writef('\n\n')
#            outf.writef('ASSERT(__box_%s_heap_end - __box_%s_heap > %s,\n' %
#                '__heap_min + __stack_min' if heapsize and stacksize else
#                '__heap_min' if heapsize else
#                '__stack_min')
#            outf.writef(4*' '+'"Not enough memory remains for heap and stack")')


#        output.append_decl('/* box memory regions */')
#        for memory in sorted(box.memories.values(), key=lambda m: m.start):
#            output.append_decl('%-32s = %#010x;' % (
#                '__box_%s_%s' % (box.name, memory.name),
#                memory.start))
#            output.append_decl('%-32s = %#010x;' % (
#                '__box_%s_%s_size' % (box.name, memory.name),
#                memory.size))
#            output.append_decl('%-32s = %#010x;' % (
#                '__box_%s_%s_end' % (box.name, memory.name),
#                memory.start+memory.size))
#        output.append_decl()
#
#        # don't forget export table location
#        # TODO need this?
#        # TODO rename?
#        output.append_decl('/* export table */')
#        output.append_decl('%-32s = __box_%s_%s;' % (
#            '__%s_exportjumptable' % box.name,
#            box.name,
#            sorted([m for m in box.memories.values() if 'r' in m.mode],
#                key=lambda m: m.start)[0].name))



#       TODO below is an implementation that relies on memory regions
#        for memory in sorted(box.memories.values(), key=lambda m: m.start):
#            output.append_memory('%(name)-16s (%(mode)s) : '
#                'ORIGIN = %(origin)#010x, '
#                'LENGTH = %(length)#010x' % dict(
#                    name='BOX_%s_%s' % (box.name.upper(), memory.name.upper()),
#                    mode=''.join(c.upper() for c in sorted(memory.mode)),
#                    origin=memory.start or 0,
#                    length=memory.size))
#
#            config = dict(
#                name=box.name, NAME=box.name.upper(),
#                mem=memory.name, MEM=memory.name.upper())
#            outf = output.append_section()
#            outf.writef('.box.%(name)s.%(mem)s (NOLOAD) : {\n' % config)
##            outf.writef(4*' '+'. = ORIGIN(mem_box_%(name)s_%(mem)s);\n'
##                % config)
#            outf.writef(4*' '+'__box_%(name)s_%(mem)s = .;\n' % config)
#            if memory.mode == set('rx'): # TODO ???
#                outf.writef(4*' '+'__%(name)s_exportjumptable = .;\n' % config)
#            outf.writef(4*' '+'. = ORIGIN(BOX_%(NAME)s_%(MEM)s) '
#                '+ LENGTH(BOX_%(NAME)s_%(MEM)s);\n' % config)
#            outf.writef(4*' '+'__box_%(name)s_%(mem)s_end = .;\n' % config)
#            outf.writef('} > BOX_%(NAME)s_%(MEM)s\n' % config)
            

    def build_box_partial_ldscript(self, sys, box, output):
        # create box calls for imports
        output.append_decl('/* box calls */')
        for i, import_ in enumerate(it.chain(
                ['__box_fault', '__box_write'],
                (import_.name for import_ in box.exports))):
            output.append_decl('%(import_)-16s = 0x0fffc000 + %(i)d*2;',
                import_=import_,
                i=i)

    def build_box_ldscript(self, sys, box, output):
        # extra decls?
        for section in []: #box.sections.values():
            if section.size is not None:
                output.append_decl('%(section_min)-16s = %(size)#010x;',
                    section_min='__%s_min' % section.name,
                    size=section.size)

        output.append_decl('%(region)-16s = %(size)#010x;',
            region='__stack_min',
            size=box.stack.size)
        output.append_decl('%(region)-16s = %(size)#010x;',
            region='__heap_min',
            size=box.heap.size)

        output.append_decl()
        self.build_box_partial_ldscript(sys, box, output)

        # create memories
        for memory in box.memories:
            output.append_memory('%(name)-16s (%(mode)s) : '
                'ORIGIN = %(origin)#010x, '
                'LENGTH = %(length)#010x',
                    name=memory.name.upper(),
                    mode=''.join(c.upper() for c in sorted(memory.mode)),
                    origin=memory.addr,
                    length=memory.size)

        # create sections
        for name in ['text', 'data', 'bss'] + sorted(
                name for name in [] #box.sections
                if name not in {'text', 'bss', 'data', 'heap', 'stack'}):
            section = None # box.sections.get(name)
            align = (section.align if section else 4) or 4
            if name in {'text'}:
                bestmemory = box.bestmemory('rx')
            elif name in {'data', 'bss'}:
                bestmemory = box.bestmemory('rw')
#            bestmemory = None
#            for memory in box.memories.values():
#                if memory.sections is not None and name in memory.sections:
#                    bestmemory = memory
#                    break
#            else:
#                if name in {'text'}:
#                    bestmemory = (sorted(
#                        [m for m in box.memories.values()
#                        if set('rx').issubset(m.mode)],
#                        key=lambda m: ('w' in m.mode)*(2<<32) - m.size)
#                            +[None])[0]
#                elif name in {'data', 'bss'}:
#                    bestmemory = (sorted(
#                        [m for m in box.memories.values()
#                        if set('rw').issubset(m.mode)],
#                        key=lambda m: -m.size)
#                            +[None])[0]

            outf = output.append_section()
            outf.writef(
                '.%(name)s%(type)s :%(at)s {\n'
                +4*' '+'. = ALIGN(%(align)d);\n'
                +4*' '+'__%(name)s = .;\n',
                name=name,
                type=' (NOLOAD)' if name == 'bss' else '',
                at=' AT(__data_init)' if name == 'data' else '',
                align=align)
            if name == 'text':
                outf.writef(4*' '+'__jumptable = .;\n')
                outf.writef(4*' '+'KEEP(*(.jumptable))\n')
            outf.writef(4*' '+'*(.%(name)s*)\n', name=name)
            if name == 'text':
                outf.writef(4*' '+'*(.rodata*)\n')
                outf.writef(4*' '+'KEEP(*(.init))\n') # TODO can these be wildcarded?
                outf.writef(4*' '+'KEEP(*(.fini))\n')
            elif name == 'bss':
                outf.writef(4*' '+'*(COMMON)\n') # TODO need this?
            outf.writef(4*' '+'. = ALIGN(%(align)d);\n', align=align)
            outf.writef(4*' '+'__%(name)s_end = .;\n', name=name)
            if name == 'text':
                outf.writef(4*' '+'__data_init = .;\n')
            outf.writef('} > %(MEM)s\n',
                MEM=bestmemory.name.upper() if bestmemory else '?')

        # here we handle heap/stack separately, they're a bit special since
        # the heap/stack can "share" memory
#        heapsection = box.sections.get('heap')
#        heapalign = (heapsection.align if heapsection else 8) or 8
#        heapsize = heapsection.size
#        stacksection = box.sections.get('stack')
#        stackalign = (stacksection.align if stacksection else 8) or 8
#        stacksize = stacksection.size
        heapalign = 8 # (heapsection.align if heapsection else 8) or 8
        heapsize = box.heap.size
        stackalign = 8 # (stacksection.align if stacksection else 8) or 8
        stacksize = box.stack.size
        bestmemory = box.bestmemory('rw')
#        bestmemory = None
#        for memory in box.memories.values():
#            if memory.sections is not None and 'heap' in memory.sections:
#                bestmemory = memory
#        else:
#            bestmemory = (sorted(
#                [m for m in box.memories.values()
#                if set('rw').issubset(m.mode)],
#                key=lambda m: -m.size)
#                    +[None])[0]

        outf = output.append_section()
        outf.writef(
            '.heap (NOLOAD) : {\n'
            +4*' '+'. = ALIGN(%(align)d);\n'
            +4*' '+'__heap = .;\n'
            +4*' '+'__stack = .;\n'
        # TODO do we need _all_ of these?
            +4*' '+'__end__ = .;\n'
            +4*' '+'PROVIDE(end = .);\n'
            +4*' '+'__HeapBase = .;\n'
            +4*' '+'__HeapLimit  = (ORIGIN(%(MEM)s) + LENGTH(%(MEM)s));\n'
            +4*' '+'__heap_limit = (ORIGIN(%(MEM)s) + LENGTH(%(MEM)s));\n'
            +4*' '+'__heap_end   = (ORIGIN(%(MEM)s) + LENGTH(%(MEM)s));\n'
            +4*' '+'__stack_end  = (ORIGIN(%(MEM)s) + LENGTH(%(MEM)s));\n'
            '} > %(MEM)s',
            align=heapalign,
            MEM=bestmemory.name.upper() if bestmemory else '?')
        if heapsize or stacksize:
            outf.writef('\n\n')
            outf.writef('ASSERT(__HeapLimit - __HeapBase > %s,\n' %
                '__heap_min + __stack_min' if heapsize and stacksize else
                '__heap_min' if heapsize else
                '__stack_min')
            outf.writef(4*' '+'"Not enough memory remains for heap and stack")')
