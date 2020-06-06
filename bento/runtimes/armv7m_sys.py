import itertools as it
import math
from .. import argstuff
from .. import runtimes
from ..box import Section


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
        self._isr_vector = Section('isr_vector', **{**isr_vector.__dict__,
            'size': isr_vector.size
                if isr_vector.size is not None else
                0x400})

    def box_box(self, box):
        self._isr_vector.alloc(box, 'r')

        self._abort_hook = box.addimport('%s.__box_abort' % box.name,
            'fn(err32) -> void', source=self, weak=True,
            doc="May be called by a well-behaved code to terminate the box "
                "if execution can not continue. Notably used for asserts. "
                "Note that __box_abort may be skipped if the box is killed "
                "because of an illegal operation. Must not return.")
        self._write_hook = box.addimport('%s.__box_write' % box.name,
            'fn(i32, u8*, usize) -> errsize', source=self, weak=True,
            doc="Provides a minimal implementation of stdout to the box. "
                "The exact behavior depends on the superbox's implementation "
                "of __box_write. If none is provided, __box_write links but "
                "does nothing.")
        self._child_write_hooks = []
        for child in box.boxes:
            self._child_write_hooks.append(box.addimport(
                '%s.__box_%s_write' % (box.name, child.name),
                'fn(i32, u8*, usize) -> errsize', source=self, weak=True,
                doc="Override __box_write for a specific box."))

        if not self._no_startup:
            self._main_hook = box.addimport('%s.__box_main' % box.name,
                'fn() -> void', source=self,
                doc="Entry point to the program.")

            # link isr vector entries
            self._esr_hooks = [
                box.addimport('%s.__box_nmi_handler' % box.name,
                    'fn() -> void', source=self, weak=True),
                box.addimport('%s.__box_hardfault_handler' % box.name,
                    'fn() -> void', source=self, weak=True),
                box.addimport('%s.__box_memmanage_handler' % box.name,
                    'fn() -> void', source=self, weak=True),
                box.addimport('%s.__box_busfault_handler' % box.name,
                    'fn() -> void', source=self, weak=True),
                box.addimport('%s.__box_usagefault_handler' % box.name,
                    'fn() -> void', source=self, weak=True),
                None,
                None,
                None,
                None,
                box.addimport('%s.__box_svc_handler' % box.name,
                    'fn() -> void', source=self, weak=True),
                box.addimport('%s.__box_debugmon_handler' % box.name,
                    'fn() -> void', source=self, weak=True),
                None,
                box.addimport('%s.__box_svc_handler' % box.name,
                    'fn() -> void', source=self, weak=True),
                box.addimport('%s.__box_systick_handler' % box.name,
                    'fn() -> void', source=self, weak=True),
            ]

            self._isr_hooks = []
            for i in range(self._isr_vector.size//4 - 16):
                self._isr_hooks.append(box.addimport(
                    '%s.__box_irq%d_handler' % (box.name, i),
                    'fn() -> void', source=self, weak=True))

        super().box_box(box)

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
        # default write/abort hooks
        output.decls.append('//// stdout implementation ////')
        if not self._abort_hook.link:
            out = output.decls.append()
            out.printf('void __box_abort(int err) {')
            with out.indent():
                out.printf('// no other course of action, so we spin')
                out.printf('while (1) {}')
            out.printf('}')

        if not self._write_hook.link:
            out = output.decls.append()
            out.printf('ssize_t __box_write(int32_t fd, '
                'void *buffer, size_t size) {')
            with out.indent():
                out.printf('return size;')
            out.printf('}')

        for hook, child in zip(self._child_write_hooks, box.boxes):
            if not hook.link:
                out.printf('#define __box_%(box)s_write __box_write',
                    box=child.name)

        output.decls.append(BOX_WRITE)

        if not self._no_startup:
            output.decls.append('//// ISR Vector definitions ////')

            # create entry point
            output.decls.append(RESET_HANDLER,
                name='__box_reset_handler',
                doc='Reset Handler',
                main=self._main_hook.link.export.alias)

            # create default isr
            output.decls.append(DEFAULT_HANDLER,
                name='__box_default_handler')

            # forward declare internal exports as needed
            out = output.decls.append()
            for handler in it.chain(self._esr_hooks, self._isr_hooks):
                if (handler and handler.link and
                        handler.link.export.source != box):
                    out.printf('void %(name)s(void);', name=handler.alias)

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
                    out.printf('(uint32_t)%(handler)s,', handler=
                        0
                        if not esr else
                        '__box_default_handler'
                        if not esr.link else
                        esr.alias)
                out.printf('// External IRQ handlers')
                for isr in self._isr_hooks:
                    out.printf('(uint32_t)%(handler)s,', handler=
                        0
                        if not isr else
                        '__box_default_handler'
                        if not isr.link else
                        isr.alias)
            out.printf('};')
