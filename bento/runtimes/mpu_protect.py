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

BOX_SYS_MECH = """
// externally declared
extern const struct %(box)s_exportjumptable __box_%(box)s_jumptable;
extern const struct %(box)s_importjumptable __%(box)s_importjumptable;
extern uint32_t __box_%(box)s_text;
extern uint32_t __box_%(box)s_etext;

// box state
const void *__box_%(box)s_table;
const void *__box_%(box)s_savedtable;
uint32_t *__box_%(box)s_savedsp;
uint32_t __box_%(box)s_savedlr;
uint32_t __box_%(box)s_savedcontrol;

// hooks for box IPC
__attribute__((naked, noreturn))
void __box_%(box)s_call(uint32_t addr, uint32_t *sp, uint32_t lr) {
    register uint32_t *args;
    __asm__ volatile (
        // save ref to args
        "mov %%1, %%0 \\n"
        // save core registers
        "stmdb %%0!, {r4-r11} \\n"
        // save fp registers?
        "tst %%2, #0x10 \\n"
        "it eq \\n"
        "vstmdbeq %%0!, {s16-s31} \\n"
        // need to update our own sp?
        "tst %%2, #0x4 \\n"
        "it eq \\n"
        "moveq sp, %%0 \\n"
        //"msreq msp, %%0 \\n"
        : "+l" (sp), "=l" (args)
        : "l" (lr)
    );

    register uint32_t *newsp = __box_%(box)s_savedsp;
    __box_%(box)s_savedsp = sp;
    register uint32_t newlr = __box_%(box)s_savedlr;
    __box_%(box)s_savedlr = lr;
    register uint32_t newcontrol = __box_%(box)s_savedcontrol;
    __box_%(box)s_savedcontrol = __get_CONTROL();
    __set_CONTROL(newcontrol);
    __ISB();

    // TODO assert newsp in range
    // TODO assert target in range

    register uint32_t target;
    if (__box_%(box)s_table == &__box_%(box)s_jumptable) {
        // into box
        target = ((const uint32_t*)__box_%(box)s_table)[(addr & 0xfff)/2 + 1];
        __box_%(box)s_savedtable = __box_%(box)s_table;
        __box_%(box)s_table = &__%(box)s_importjumptable;
    } else  {
        // out of box
        target = ((const uint32_t*)__box_%(box)s_table)[(addr & 0xfff)/2];
        __box_%(box)s_savedtable = __box_%(box)s_table;
        __box_%(box)s_table = &__box_%(box)s_jumptable;
    }
   
    newsp -= 8;
    newsp[0] = args[0];     // r0 = arg0
    newsp[1] = args[1];     // r1 = arg1
    newsp[2] = args[2];     // r2 = arg2
    newsp[3] = args[3];     // r3 = arg3
    newsp[4] = args[4];     // r12 = r12
    newsp[5] = 0x0fffd000;  // lr = __box_%(box)s_ret
    newsp[6] = target;      // pc = target
    newsp[7] = args[7];     // psr = psr 

    __asm__ volatile (
        // update sp
        "tst %%1, #0x4 \\n"
        "ite eq \\n"
        "msreq msp, %%0 \\n"
        "msrne psp, %%0 \\n"
        // branch to call
        "bx %%1 \\n"
        :
        : "l" (newsp), "r" (newlr)
    );

    __builtin_unreachable();
}

__attribute__((noreturn))
void __box_%(box)s_ret(uint32_t *sp, uint32_t lr) {
    // grab args and remove saved stack frame
    uint32_t *args = sp;
    sp += 8;

    const void *newtable = __box_%(box)s_savedtable;
    __box_%(box)s_savedtable = __box_%(box)s_table;
    __box_%(box)s_table = newtable;
    register uint32_t *newsp __asm__("r0") = __box_%(box)s_savedsp;
    __box_%(box)s_savedsp = sp;
    register uint32_t newlr __asm__("r1") = __box_%(box)s_savedlr;
    __box_%(box)s_savedlr = lr;
    uint32_t newcontrol = __box_%(box)s_savedcontrol;
    __box_%(box)s_savedcontrol = __get_CONTROL();
    __set_CONTROL(newcontrol);
    __ISB();

    __asm__ volatile (
        // restore fp registers?
        // we do this here to make accessing the return frame easier
        "tst %%1, #0x10 \\n"
        "it eq \\n"
        "vldmiaeq %%0!, {s16-s31} \\n"
        : "+l" (newsp)
        : "l" (newlr)
    );

    // update registers with return value(s)
    newsp[8+0] = args[0];
    newsp[8+1] = args[1];
    newsp[8+2] = args[2];
    newsp[8+3] = args[3];

    // set new pc to our real return location
    newsp[8+6] = newsp[8+5];

    // return the other register and return
    __asm__ volatile (
        // restore core registers
        "ldmia %%0!, {r4-r11} \\n"
        // update sp
        "tst %%1, #0x4 \\n"
        "ite eq \\n"
        "msreq msp, %%0 \\n"
        "msrne psp, %%0 \\n"
        // return
        "bx %%1 \\n"
        :
        : "l" (newsp), "l" (newlr)
    );

    __builtin_unreachable();
}

//__attribute__((alias("BusFault_Handler")))
//void MemManage_Handler(void);
__attribute__((naked))
void BusFault_Handler(void) {
    register uint32_t *sp __asm__("r0");
    register uint32_t lr __asm__("r1");
    __asm__ volatile (
        // get lr, sp, and args
        "mov %%1, lr \\n"
        "tst %%1, #0x4 \\n"
        "ite eq \\n"
        "mrseq %%0, msp \\n"
        "mrsne %%0, psp \\n"
        : "=l" (sp), "=l" (lr)
    );

    uint32_t op = sp[6];
    switch (op & ~0xfff) {
        case 0x0fffc000:
            __box_%(box)s_call(op, sp, lr);
            break;
        case 0x0fffd000:
            __box_%(box)s_ret(sp, lr);
            break;
    }

    // normal access violation, report
    __box_%(box)s_call(0, sp, lr);

    // shouldn't get here, but just in case
    while (1) {}
}

void __box_%(box)s_init(void) {
    // set up stack pointer
    __box_%(box)s_table = &__box_%(box)s_jumptable;
    __box_%(box)s_savedtable = &__%(box)s_importjumptable;
    __box_%(box)s_savedsp = __box_%(box)s_jumptable
            .__box_%(box)s_stack_end;
    __box_%(box)s_savedlr = 0xfffffffd; // TODO need fp bit?
    __box_%(box)s_savedcontrol = __get_CONTROL() | 1; // unprivileged

    extern void __box_%(box)s_boxinit(const void *);
    __box_%(box)s_boxinit(&__%(box)s_importjumptable);
}

void __box_%(box)s_fault(void) {
    // report access violation along with address
    uint32_t addr = *(uint32_t*)0xE000ED38;
    extern void __box_%(box)s_fault_handler(uint32_t addr);
    __box_%(box)s_fault_handler(addr);
}
"""

@runtimes.runtime
class MPUProtectRuntime(runtimes.Runtime):
    """
    A bento-box runtime that uses a v7 MPU to provide memory isolation
    between boxes.
    """
    __argname__ = "armv7_mpu"
    __arghelp__ = __doc__
#
#    # TODO dupe to Runtime
#    def box(self, box):
#        self.box = box

#    def build_common_header_glue_(self, output):
#        output.includes.append("<sys/types.h>")
#        output.decls.append('void __box_%(box)s_init(void);',
#            doc='jumptable initialization')

    def build_common_c_glue_(self, box, output):
        output.decls.append('//// jumptable declarations ////')

        outf = output.decls.append()
        outf.write('struct %(box)s_exportjumptable {\n')
        with outf.pushindent():
            # special entries for the sp and __box_init
            outf.write('uint32_t *__box_%(box)s_stack_end;\n')
            outf.write('void (*__box_%(box)s_init)(void);\n')
            for export in box.exports:
                outf.write('%(fn)s;\n', fn=export.repr_c_ptr())
        outf.write('};\n')

        outf = output.decls.append()
        outf.write('struct %(box)s_importjumptable {\n')
        with outf.pushindent():
            # special entries for __box_write and __box_fault
            outf.write('void (*__box_%(box)s_fault)(void);\n')
            outf.write('int (*__box_%(box)s_write)('
                'int a, char* b, int c);\n') # TODO are these the correct types??
            for import_ in box.imports:
                outf.write('%(fn)s;\n', fn=import_.repr_c_ptr())
        outf.write('};\n')

    def build_sys_c_glue_(self, sys, box, output):
        self.build_common_c_glue_(box, output)

        output.decls.append('//// jumptable implementation ////')
        output.includes.append('"fsl_sysmpu.h"')
        output.decls.append(
            'extern int _write(int handle, char *buffer, int size);',
            doc='GCC stdlib hook')

        # TODO should this be split?
        output.decls.append(BOX_SYS_MECH)

        outf = output.decls.append(doc='system-side jumptable')
        outf.write('const struct %(box)s_importjumptable '
            '__%(box)s_importjumptable = {\n')
        with outf.pushindent():
            # special entries for __box_fault and __box_write
            outf.write('__box_%(box)s_fault,\n')
            outf.write('_write,\n')
            for import_ in box.imports:
                outf.write('%(import_)s,\n', import_=import_.name)
        outf.write('};\n')

    def build_box_c_glue_(self, box, output):
        self.build_common_c_glue_(box, output)

        output.decls.append('//// jumptable implementation ////')
        output.decls.append(BOX_INIT)
        output.decls.append(BOX_WRITE)

        output.decls.append('extern uint32_t __stack_end;')
        outf = output.decls.append(doc='box-side jumptable')
        outf.write('__attribute__((section(".jumptable")))\n')
        outf.write('__attribute__((used))\n')
        outf.write('const struct %(box)s_exportjumptable '
            '__box_%(box)s_jumptable = {\n')
        with outf.pushindent():
            # special entries for the sp and __box_init
            outf.write('&__stack_end,\n')
            outf.write('__box_%(box)s_init,\n')
            for export in box.exports:
                outf.write('%(export)s,\n', export=export.name)
        outf.write('};\n')

    def build_sys_ldscript_(self, sys, box, output): # TODO hmm on this partial thing...
        # create box calls for imports
        output.decls.append()
        output.decls.append('/* box calls */')
        for i, import_ in enumerate(it.chain(
                # TODO rename this
                ['__box_%(box)s_boxinit'],
                (import_.name for import_ in box.exports))):
            output.decls.append('%(import_)-24s = 0x0fffc000 + %(i)d*2;',
                import_=import_,
                i=i)

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
        memory = box.bestmemory('rx', box.jumptable.size,
            consumed=output.consumed)
        outf = output.sections.insert(0,
            box_memory=memory.name,
            section='.box.%(box)s.%(box_memory)s',
            memory='box_%(box)s_%(box_memory)s')
        outf.write('. = ORIGIN(%(MEMORY)s);\n')
        outf.write('__box_%(box)s_jumptable = .;')

    def build_box_partial_ldscript_(self, box, output):
        if output['section_prefix'] == '.':
            # create box calls for imports
            output.decls.append()
            output.decls.append('/* box calls */')
            for i, import_ in enumerate(it.chain(
                    ['__box_fault', '__box_write'],
                    (import_.name for import_ in box.imports))):
                output.decls.append('%(import_)-24s = 0x0fffc000 + %(i)d*2;',
                    import_=import_,
                    i=i)

    def build_box_ldscript_(self, box, output):
        self.build_box_partial_ldscript_(box, output)

        
        # TODO handle this in ldscript class? ldscript.consume?
        # TODO make jumptable come before ldscript declarations.
        # Need box method?
        # TODO what... this just doesn't work...
        memory = box.bestmemory('rx', box.jumptable.size,
            consumed=output.consumed)
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
        outf.write('%(section)s : {\n')
        with outf.pushindent():
            outf.write('. = ALIGN(%(align)d);\n')
            outf.write('%(symbol_prefix)sjumptable = .;\n')
            outf.write('KEEP(*(%(section_prefix)sjumptable))\n')
            outf.write('. = ALIGN(%(align)d);\n')
            outf.write('%(symbol_prefix)sjumptable_end = .;\n')
        outf.write('} > %(MEMORY)s')

    def build(self):
        self.box.parentbuild('c_glue_', self.build_sys_c_glue_)
        self.box.build('c_glue_', self.build_box_c_glue_)
        self.box.parentbuild('ldscript_', self.build_sys_ldscript_)
        self.box.build('ldscript_', self.build_box_ldscript_)
        self.box.parentbuild('partial_ldscript_', self.build_sys_ldscript_)
        self.box.build('partial_ldscript_', self.build_box_partial_ldscript_)
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
        

    def build_common_header_glue_(self, sys, box, output):
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
        outf.write('struct %(box)s_exportjumptable {\n')
        # special entries for the sp and __box_init
        outf.write('    uint32_t *__box_%(box)s_stack_end;\n')
        outf.write('    void (*__box_%(box)s_init)(void);\n')
        for export in box.exports:
            outf.write('    %(fn)s;\n', fn=export.repr_c_ptr())
#            outf.write('    %(ret)s (*%(export)s)(%(args)s);\n',
#                export=export.name,
#                args='void' if not export.args else ', '.join(
#                    arg.repr_c(name) for arg, name in zip(
#                        export.args, util.arbitrary())),
#                ret='void' if not export.rets else export.rets[0].repr_c())
        outf.write('};\n')

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
        outf.write('struct %(box)s_importjumptable {\n')
        # special entries for __box_write and __box_fault
        outf.write('    void (*__box_%(box)s_fault)(void);\n')
        outf.write('    int (*__box_%(box)s_write)('
            'int a, char* b, int c);\n')
        for import_ in box.imports:
            outf.write('    %(fn)s;\n', fn=import_.repr_c_ptr())
#            outf.write('    %(ret)s (*%(import_)s)(%(args)s);\n',
#                import_=import_.name,
#                args='void' if not import_.args else ', '.join(
#                    arg.repr_c(name) for arg, name in zip(
#                        import_.args, util.arbitrary())),
#                ret='void' if not import_.rets else import_.rets[0].repr_c())
        outf.write('};\n')

#    def build_common_header_(self, outf, sys, box):
#        outf.write('// exports from box %s\n' % box.name)
#        # TODO error if import not found?
#        for export in box.exports.values():
#            assert len(export.rets) <= 1
#            outf.write('extern %(ret)s %(name)s(%(args)s);\n' % dict(
#                name=export.name,
#                args='void' if not export.args else ', '.join(
#                    '%s %s' % arg for arg in zip(
#                        export.args, util.arbitrary())),
#                ret='void' if not export.rets else export.rets[0]))
#        outf.write('\n')
#        outf.write('struct %s_exportjumptable {\n' % box.name)
#        # special entries for the sp and __box_init
#        outf.write('    uint32_t *__box_%s_stack_end;\n' % box.name)
#        outf.write('    void (*__box_%s_init)(void);\n' % box.name)
#        for export in box.exports.values():
#            outf.write('    %(ret)s (*%(name)s)(%(args)s);\n' % dict(
#                name=export.name,
#                args='void' if not export.args else ', '.join(
#                    '%s %s' % arg for arg in zip(
#                        export.args, util.arbitrary())),
#                ret='void' if not export.rets else export.rets[0]))
#        outf.write('};\n')
#        outf.write('\n')
#
#        outf.write('// imports from box %s\n' % box.name)
#        # TODO error if import not found?
#        for import_ in box.imports.values():
#            assert len(import_.rets) <= 1
#            outf.write('extern %(ret)s %(name)s(%(args)s);\n' % dict(
#                name=import_.name,
#                args='void' if not import_.args else ', '.join(
#                    '%s %s' % arg for arg in zip(
#                        import_.args, util.arbitrary())),
#                ret='void' if not import_.rets else import_.rets[0]))
#        outf.write('\n')
#        outf.write('struct %s_importjumptable {\n' % box.name)
#        # special entries for __box_write and __box_fault
#        outf.write('    void (*__box_%s_write)('
#            'int a, char* b, int c);\n' % box.name)
#        outf.write('    void (*__box_%s_fault)(void);\n' % box.name)
#        for import_ in box.imports.values():
#            outf.write('    %(ret)s (*%(name)s)(%(args)s);\n' % dict(
#                name=import_.name,
#                args='void' if not import_.args else ', '.join(
#                    '%s %s' % arg for arg in zip(
#                        import_.args, util.arbitrary())),
#                ret='void' if not import_.rets else import_.rets[0]))
#        outf.write('};\n')
#        outf.write('\n')

    def build_sys_header_glue_(self, sys, box, output):
        """Build system header"""
        output.includes.append("<sys/types.h>")

#        outf = output.decls.append()
#        outf.write('// jumptable initialization\n')
#        outf.write('void __box_%(box)s_init(void);\n')
#        output.decls.append(fn=Fn(
#            '__box_%(box)s_init', 'fn() -> void',
#            doc='jumptable initialization'))
        output.decls.append('void __box_%(box)s_init(void);',
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
        outf.write('struct %(box)s_exportjumptable {\n')
        # special entries for the sp and __box_init
        outf.write('    uint32_t *__box_%(box)s_stack_end;\n')
        outf.write('    void (*__box_%(box)s_init)(void);\n')
        for export in box.exports:
            outf.write('    %(fn)s;\n', fn=export.repr_c_ptr())
#            outf.write('    %(ret)s (*%(export)s)(%(args)s);\n',
#                export=export.name,
#                args='void' if not export.args else ', '.join(
#                    arg.repr_c(name) for arg, name in zip(
#                        export.args, util.arbitrary())),
#                ret='void' if not export.rets else export.rets[0].repr_c())
        outf.write('};\n')

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
        outf.write('struct %(box)s_importjumptable {\n')
        # special entries for __box_write and __box_fault
        outf.write('    void (*__box_%(box)s_fault)(void);\n')
        outf.write('    int (*__box_%(box)s_write)('
            'int a, char* b, int c);\n')
        for import_ in box.imports:
            outf.write('    %(fn)s;\n', fn=import_.repr_c_ptr())
#            outf.write('    %(ret)s (*%(import_)s)(%(args)s);\n',
#                import_=import_.name,
#                args='void' if not import_.args else ', '.join(
#                    arg.repr_c(name) for arg, name in zip(
#                        import_.args, util.arbitrary())),
#                ret='void' if not import_.rets else import_.rets[0].repr_c())
        outf.write('};\n')

#    def build_common_header_(self, outf, sys, box):
#        outf.write('// exports from box %s\n' % box.name)
#        # TODO error if import not found?
#        for export in box.exports.values():
#            assert len(export.rets) <= 1
#            outf.write('extern %(ret)s %(name)s(%(args)s);\n' % dict(
#                name=export.name,
#                args='void' if not export.args else ', '.join(
#                    '%s %s' % arg for arg in zip(
#                        export.args, util.arbitrary())),
#                ret='void' if not export.rets else export.rets[0]))
#        outf.write('\n')
#        outf.write('struct %s_exportjumptable {\n' % box.name)
#        # special entries for the sp and __box_init
#        outf.write('    uint32_t *__box_%s_stack_end;\n' % box.name)
#        outf.write('    void (*__box_%s_init)(void);\n' % box.name)
#        for export in box.exports.values():
#            outf.write('    %(ret)s (*%(name)s)(%(args)s);\n' % dict(
#                name=export.name,
#                args='void' if not export.args else ', '.join(
#                    '%s %s' % arg for arg in zip(
#                        export.args, util.arbitrary())),
#                ret='void' if not export.rets else export.rets[0]))
#        outf.write('};\n')
#        outf.write('\n')
#
#        outf.write('// imports from box %s\n' % box.name)
#        # TODO error if import not found?
#        for import_ in box.imports.values():
#            assert len(import_.rets) <= 1
#            outf.write('extern %(ret)s %(name)s(%(args)s);\n' % dict(
#                name=import_.name,
#                args='void' if not import_.args else ', '.join(
#                    '%s %s' % arg for arg in zip(
#                        import_.args, util.arbitrary())),
#                ret='void' if not import_.rets else import_.rets[0]))
#        outf.write('\n')
#        outf.write('struct %s_importjumptable {\n' % box.name)
#        # special entries for __box_write and __box_fault
#        outf.write('    void (*__box_%s_write)('
#            'int a, char* b, int c);\n' % box.name)
#        outf.write('    void (*__box_%s_fault)(void);\n' % box.name)
#        for import_ in box.imports.values():
#            outf.write('    %(ret)s (*%(name)s)(%(args)s);\n' % dict(
#                name=import_.name,
#                args='void' if not import_.args else ', '.join(
#                    '%s %s' % arg for arg in zip(
#                        import_.args, util.arbitrary())),
#                ret='void' if not import_.rets else import_.rets[0]))
#        outf.write('};\n')
#        outf.write('\n')

    def build_sys_header_glue(self, sys, box, output):
        """Build system header"""
        output.append_include("<sys/types.h>")

        outf = output.append_decl()
        outf.write('// jumptable initialization\n')
        outf.write('void __box_%(box)s_init(void);\n')

        self.build_common_header_glue(sys, box, output)

#    def build_sys_header_(self, outf, sys, box):
#        """Build system header for a given box into the given file."""
#        outf.write('////// AUTOGENERATED //////\n')
#        outf.write('#ifndef %s_JUMPTABLE_H\n' % box.name.upper())
#        outf.write('#define %s_JUMPTABLE_H\n' % box.name.upper())
#        outf.write('\n')
#        outf.write('#include <sys/types.h>\n') # this should be consolidated
#        outf.write('\n')
#
#        outf.write('// jumptable initialization\n')
#        outf.write('void __box_%s_init(void);\n' % box.name)
#        outf.write('\n')
#
#        self.build_common_header_(outf, sys, box)
#
#        outf.write('#endif\n')
#        outf.write('\n')

    def build_sys_c_glue_prologue(self, sys, output):
        outf = output.append_decl()
        outf.write('// GCC stdlib hook\n')
        outf.write('extern int _write(int handle, char *buffer, int size);\n')

    def build_sys_c_glue(self, sys, box, output):
        self.build_common_header_glue(sys, box, output)
        output.append_include('"fsl_sysmpu.h"')

        # TODO should this be split?
        output.append_decl(BOX_SYS_MECH.lstrip())

        outf = output.append_decl()
        outf.write('// system-side jumptable\n')
        outf.write('const struct %(box)s_importjumptable '
            '__%(box)s_importjumptable = {\n')
        # special entries for __box_fault and __box_write
        outf.write('    __box_%(box)s_fault,\n')
        outf.write('    _write,\n')
        for import_ in box.imports:
            outf.write('    %(import_)s,\n', import_=import_.name)
        outf.write('};\n')

#    def build_sys_jumptable_(self, outf, sys, box):
#        """Build system jumptable for a given box into the given file."""
#        # we don't know if user requested header generation, so we just
#        # duplicate it here
#        # TODO need this?
#        self.build_sys_header_(outf, sys, box)
#
#        outf.write('// GCC stdlib hook\n')
#        outf.write('extern int _write(int handle, char *buffer, int size);\n')
#        outf.write('\n')
#
#        outf.write(BOX_SYS_MECH.strip() % dict(name=box.name))
#        outf.write('\n')
#        outf.write('\n')
#
#        outf.write('// system-side jumptable\n')
#        outf.write('const struct %(name)s_importjumptable '
#            '__%(name)s_importjumptable = {' % dict(name=box.name))
#        # special entries for __box_fault and __box_write
#        outf.write('    __box_fault,\n')
#        outf.write('    _write,\n')
#        for import_ in box.imports.values():
#            outf.write('    %s,\n' % import_.name)
#        outf.write('};\n')
#        outf.write('\n')

#    def build_sys_ldscript_(self, outf, sys, box):
#        """Build system ldscript for a given box into the given file."""

    def build_box_header_glue(self, sys, box, output):
        self.build_common_header_glue(sys, box, output)

#    def build_box_header_(self, outf, sys, box):
#        """Build system header for a given box into the given file."""
#        outf.write('////// AUTOGENERATED //////\n')
#        outf.write('#ifndef %s_JUMPTABLE_H\n' % box.name.upper())
#        outf.write('#define %s_JUMPTABLE_H\n' % box.name.upper())
#        outf.write('\n')
#        outf.write('#include <sys/types.h>\n') # this should be consolidated
#        outf.write('\n')
#
#        self.build_common_header_(outf, sys, box)
#
#        outf.write('#endif\n')
#        outf.write('\n')

    def build_box_c_glue(self, sys, box, output):
        self.build_common_header_glue(sys, box, output)

        output.append_decl(BOX_INIT.lstrip())
        output.append_decl(BOX_WRITE.lstrip())

        output.append_decl('extern uint32_t __stack_end;')
        outf = output.append_decl()
        outf.write('__attribute__((section(".jumptable")))\n')
        outf.write('__attribute__((used))\n')
        outf.write('const struct %(box)s_exportjumptable '
            '__box_%(box)s_jumptable = {\n')
        # special entries for the sp and __box_init
        outf.write('    &__stack_end,\n')
        outf.write('    __box_%(box)s_init,\n')
        for export in box.exports:
            outf.write('    %(export)s,\n', export=export.name)
        outf.write('};\n')

#    def build_box_jumptable_(self, outf, sys, box):
#        """Build system jumptable for a given box into the given file."""
#        # we don't know if user requested header generation, so we just
#        # duplicate it here
#        # TODO need this?
#        self.build_box_header_(outf, sys, box)
#
#        outf.write(BOX_INIT.strip() % dict(name=box.name))
#        outf.write('\n')
#        outf.write('\n')
#
#        outf.write('extern uint32_t __box_%s_sp;\n' % box.name)
#        outf.write('__attribute__((section(".jumptable")))\n')
#        outf.write('__attribute__((used))\n')
#        outf.write('const struct %(name)s_exportjumptable '
#            '__%(name)s_exportjumptable = {' % dict(name=box.name))
#        # special entries for the sp and __box_init
#        outf.write('    &__stack_end,\n')
#        outf.write('    __box_%s_init,\n' % box.name)
#        for export in box.exports.values():
#            outf.write('    %s,\n' % export.name)
#        outf.write('};\n')
#        outf.write('\n')
#
#        # write handler
#        outf.write(BOX_WRITE.strip() % dict(name=box.name))
#        outf.write('\n')
#        outf.write('\n')

#    def build_box_ldscript_(self, outf, sys, box):
#        """Build system ldscript for a given box into the given file."""
#        outf.write('\n')
#
#        # TODO make heap optional?
#        outf.write('HEAP_MIN = '
#            'DEFINED(__heap_min__) ? __heap_min__ : 0x1000;\n')
#        outf.write('\n')
#
#        outf.write('MEMORY {\n')
#        for memory in box.memories.values():
#            outf.write('    mem_%(name)-16s (%(mode)s) : '
#                'ORIGIN = %(start)#010x, LENGTH = %(size)#010x\n' % dict(
#                    name=memory.name,
#                    mode=''.join(c.upper() for c in memory.mode),
#                    start=memory.start,
#                    size=memory.size))
#        outf.write('}\n')

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
            outf.write(
                '.box.%(box)s.%(name)s%(type)s :%(at)s {\n'
                +4*' '+'. = ALIGN(%(align)d);\n'
                +4*' '+'__box_%(box)s_%(name)s = .;\n',
                name=name,
                type=' (NOLOAD)' if name == 'bss' else '',
                at=' AT(__box_%s_data_init)' % box.name
                    if name == 'data' else '',
                align=align)
            if name == 'text':
                outf.write(4*' '+'__box_%(box)s_jumptable = .;\n')
                outf.write(4*' '+'__%(box)s_exportjumptable = .;\n') # TODO rename me
                #outf.write(4*' '+'KEEP(*(.box.%s.jumptable))\n' % box.name)
            outf.write(''
                +4*' '+'KEEP(*(.box.%(box)s.%(name)s*))\n'
                +4*' '+'. = ALIGN(%(align)d);\n'
                +4*' '+'__box_%(box)s_%(name)s_end = .;\n',
                name=name,
                align=align)
#            if name == 'text':
#                outf.write(4*' '+'KEEP(*(.box.%s.rodata*))\n' % box.name)
#                outf.write(4*' '+'KEEP(*(.box.%s.init))\n' % box.name) # TODO can these be wildcarded?
#                outf.write(4*' '+'KEEP(*(.box.%s.fini))\n' % box.name)
#            elif name == 'bss':
#                pass
#                #outf.write(4*' '+'*(COMMON)\n') # TODO need this?
            if name == 'text':
                outf.write(4*' '+'__box_%(box)s_data_init = .;\n')
            outf.write(
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
        outf.write(
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
#            outf.write('\n\n')
#            outf.write('ASSERT(__box_%s_heap_end - __box_%s_heap > %s,\n' %
#                '__heap_min + __stack_min' if heapsize and stacksize else
#                '__heap_min' if heapsize else
#                '__stack_min')
#            outf.write(4*' '+'"Not enough memory remains for heap and stack")')


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
#            outf.write('.box.%(name)s.%(mem)s (NOLOAD) : {\n' % config)
##            outf.write(4*' '+'. = ORIGIN(mem_box_%(name)s_%(mem)s);\n'
##                % config)
#            outf.write(4*' '+'__box_%(name)s_%(mem)s = .;\n' % config)
#            if memory.mode == set('rx'): # TODO ???
#                outf.write(4*' '+'__%(name)s_exportjumptable = .;\n' % config)
#            outf.write(4*' '+'. = ORIGIN(BOX_%(NAME)s_%(MEM)s) '
#                '+ LENGTH(BOX_%(NAME)s_%(MEM)s);\n' % config)
#            outf.write(4*' '+'__box_%(name)s_%(mem)s_end = .;\n' % config)
#            outf.write('} > BOX_%(NAME)s_%(MEM)s\n' % config)
            

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
            outf.write(
                '.%(name)s%(type)s :%(at)s {\n'
                +4*' '+'. = ALIGN(%(align)d);\n'
                +4*' '+'__%(name)s = .;\n',
                name=name,
                type=' (NOLOAD)' if name == 'bss' else '',
                at=' AT(__data_init)' if name == 'data' else '',
                align=align)
            if name == 'text':
                outf.write(4*' '+'__jumptable = .;\n')
                outf.write(4*' '+'KEEP(*(.jumptable))\n')
            outf.write(4*' '+'*(.%(name)s*)\n', name=name)
            if name == 'text':
                outf.write(4*' '+'*(.rodata*)\n')
                outf.write(4*' '+'KEEP(*(.init))\n') # TODO can these be wildcarded?
                outf.write(4*' '+'KEEP(*(.fini))\n')
            elif name == 'bss':
                outf.write(4*' '+'*(COMMON)\n') # TODO need this?
            outf.write(4*' '+'. = ALIGN(%(align)d);\n', align=align)
            outf.write(4*' '+'__%(name)s_end = .;\n', name=name)
            if name == 'text':
                outf.write(4*' '+'__data_init = .;\n')
            outf.write('} > %(MEM)s\n',
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
        outf.write(
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
            outf.write('\n\n')
            outf.write('ASSERT(__HeapLimit - __HeapBase > %s,\n' %
                '__heap_min + __stack_min' if heapsize and stacksize else
                '__heap_min' if heapsize else
                '__stack_min')
            outf.write(4*' '+'"Not enough memory remains for heap and stack")')
