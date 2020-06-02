import itertools as it
import math
from .. import argstuff
from .. import runtimes
from ..box import Section, Export


RESET_HANDLER = """
__attribute__((naked, noreturn))
void %(name)s(void) {
    __asm__ volatile (
        // disable irqs
        "cpsid i \\n\\t"

        // copy data
        "ldr r1, =__data_init \\n\\t"
        "ldr r2, =__data \\n\\t"
        "ldr r3, =__data_end \\n\\t"
    "._L0: \\n\\t"
        "cmp r2, r3 \\n\\t"
        "ittt lt \\n\\t"
        "ldrlt r0, [r1], #4 \\n\\t"
        "strlt r0, [r2], #4 \\n\\t"
        "blt ._L0 \\n\\t"

        // clear bss
        "ldr r1, =__bss \\n\\t"
        "ldr r2, =__bss_end \\n\\t"
        "movs r0, 0 \\n\\t"
    "._L1: \\n\\t"
        "cmp r1, r2 \\n\\t"
        "itt lt \\n\\t"
        "strlt r0, [r1], #4 \\n\\t"
        "blt ._L1 \\n\\t"

        // init stdlib
        "ldr r0, =__libc_init_array \\n\\t"
        "blx r0 \\n\\t"

        // enable irqs
        "cpsie i \\n\\t"

        // go to main!
        "ldr r0, =%(main)s \\n\\t"
        "blx r0 \\n\\t"

        // loop if main exits
    "._L2: \\n\\t"
        "wfi \\n\\t"
        "b ._L2 \\n\\t"
    );
}
"""

DEFAULT_HANDLER = """
__attribute__((weak, naked, noreturn))
void %(name)s(void) {
    __asm__ volatile (
        "b . \\n\\t"
    );
}
"""

BOX_WRITE = """
//__attribute__((alias("__box_write")))
int _write(int handle, char *buffer, int size) {
    extern ssize_t __box_write(int32_t handle, void *buffer, size_t size);
    // TODO hmm, why can't this alias?
    return __box_write(handle, (uint8_t*)buffer, size);
}
"""

@runtimes.runtime
class ARMv7MSysRuntime(runtimes.Runtime):
    """
    A bento-box runtime that runs in privledge mode on the system.
    Usually required at the root of the project.
    """
    __argname__ = "armv7m_sys"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser, **kwargs):
        parser.add_argument('--no_startup', type=bool,
            help="Don't emit definitions normally found in startup files.")
        parser.add_nestedparser('--isr_vector', Section)

    def __init__(self, no_startup=None, isr_vector=None):
        super().__init__()
        self._no_startup = no_startup or False 
        self._isr_vector = Section(**{**isr_vector.__dict__,
            'size': isr_vector.size
                if isr_vector.size is not None else
                0x400})

    def box_box(self, box):
        self._isr_vector.memory = box.consume('rx', section=self._isr_vector)

        box.addexport(
            '__box_fault',
            'fn(err32) -> void',
            source=self,
            weak=True)
        for child in box.boxes:
            box.addexport(
            '__box_%s_fault' % child.name,
            'fn(err32) -> void',
            source=self,
            weak=True)

        box.addexport(
            '__box_write',
            'fn(i32, u8*, usize) -> errsize',
            source=self,
            weak=True)
        for child in box.boxes:
            box.addexport(
                '__box_%s_write' % child.name,
                'fn(i32, u8*, usize) -> errsize',
                source=self,
                weak=True)

        super().box_box(box)

    def link_box(self, box):
        self._fault_hook = box.checkexport(
            '__box_fault',
            'fn(err32) -> void',
            source=self)
        self._child_fault_hooks = []
        for child in box.boxes:
            self._child_fault_hooks.append(box.checkexport(
                '__box_%s_fault' % child.name,
                'fn(err32) -> void',
                source=self))

        self._write_hook = box.checkexport(
            '__box_write',
            'fn(i32, u8*, usize) -> errsize',
            source=self)
        self._child_write_hooks = []
        for child in box.boxes:
            self._child_write_hooks.append(box.checkexport(
                '__box_%s_write' % child.name,
                'fn(i32, u8*, usize) -> errsize',
                source=self))

        if not self._no_startup:
            self._main_hook = box.checkexport(
                '__box_main',
                'fn()->void',
                source=self)

            # link isr vector entries
            self._esr_hooks = [
                box.getexport('__box_nmi_handler',
                    'fn() -> void', source=self),
                box.getexport('__box_hardfault_handler',
                    'fn() -> void', source=self),
                box.getexport('__box_memmanage_handler',
                    'fn() -> void', source=self),
                box.getexport('__box_busfault_handler',
                    'fn() -> void', source=self),
                box.getexport('__box_usagefault_handler',
                    'fn() -> void', source=self),
                None,
                None,
                None,
                None,
                box.getexport('__box_svc_handler',
                    'fn() -> void', source=self),
                box.getexport('__box_debugmon_handler',
                    'fn() -> void', source=self),
                None,
                box.getexport('__box_svc_handler',
                    'fn() -> void', source=self),
                box.getexport('__box_systick_handler',
                    'fn() -> void', source=self),
            ]

            self._isr_hooks = []
            for i in range(self._isr_vector.size//4 - 16):
                self._isr_hooks.append(box.getexport(
                    '__box_irq%d_handler' % i, 'fn() -> void', source=self))

    def build_box_ld(self, output, box):
        # reset handler
        output.decls.append('ENTRY(__box_reset_handler)')

        # interrupt vector
        if self._isr_vector:
            out = output.sections.append(
                section='.isr_vector',
                memory=self._isr_vector.memory.name)
            out.printf('.isr_vector : {')
            with out.pushindent():
                out.printf('. = ALIGN(%(align)d);')
                out.printf('__isr_vector = .;')
                out.printf('KEEP(*(.isr_vector))')
                out.printf('. = __isr_vector + %(isr_vector_size)#x;',
                    isr_vector_size=self._isr_vector.size)
                out.printf('. = ALIGN(%(align)d);')
                out.printf('__isr_vector_end = .;')
            out.printf('} > %(MEMORY)s')

        super().build_box_ld(output, box)

    def build_box_c(self, output, box):
        output.decls.append('//// box hook ////')
        # default fault hooks
        # TODO don't always emit __box_fault?
        if self._fault_hook.source == self:
            out = output.decls.append()
            out.printf('static void __box_fault(int err) {')
            out.printf('}')

        out = output.decls.append()
        for hook, child in zip(self._child_fault_hooks, box.boxes):
            if hook.source == self:
                out.printf('#define __box_%(box)s_fault %(alias)s',
                    box=child.name, alias=self._fault_hook.alias)

        # default write hooks
        if self._write_hook.source == self:
            out = output.decls.append()
            out.printf('int __box_write(int32_t fd, '
                'uint8_t *buffer, size_t size) {')
            with out.indent():
                out.printf('return size;')
            out.printf('}')

        out = output.decls.append()
        for hook, child in zip(self._child_write_hooks, box.boxes):
            if hook.source == self:
                out.printf('#define __box_%(box)s_write %(alias)s',
                    box=child.name, alias=self._write_hook.alias)

        output.decls.append('//// stdout implementation ////')
        output.decls.append(BOX_WRITE)

        if not self._no_startup:
            output.decls.append('//// ISR Vector definitions ////')

            # create entry point
            output.decls.append(RESET_HANDLER,
                name='__box_reset_handler',
                doc='Reset Handler',
                main=self._main_hook.alias)

            # forward declare these
            # TODO use export/import utilities to hook these in same box?
            out = output.decls.append()
            out.printf('void __box_memmanage_handler(void);')
            out.printf('void __box_busfault_handler(void);')
            out.printf('void __box_usagefault_handler(void);')

            # create default isr
            output.decls.append(DEFAULT_HANDLER,
                name='__box_default_handler')

            output.decls.append('extern uint32_t __stack_end;')

            # now create actual vector table
            output.decls.append('//// ISR Vector ////')
            out = output.decls.append(
                size=2+len(self._esr_hooks)+len(self._isr_hooks))
            out.printf('__attribute__((section(".isr_vector")))')
            out.printf('const uint32_t __isr_vector[%(size)d] = {')
            with out.indent():
                out.printf('(uint32_t)&__stack_end,')
                out.printf('(uint32_t)&__box_reset_handler,')
                out.printf('// Exception handlers')
                for esr in self._esr_hooks:
                    out.printf('(uint32_t)%(name)s,',
                        name=esr.alias if esr else '__box_default_handler')
                out.printf('// External IRQ handlers')
                for isr in self._isr_hooks:
                    out.printf('(uint32_t)%(name)s,',
                        name=isr.alias if isr else '__box_default_handler')
            out.printf('};')
