import itertools as it
import math
from .. import argstuff
from .. import runtimes
from ..box import Section
from ..glue.error_glue import ErrorGlue
from ..glue.write_glue import WriteGlue
from ..glue.abort_glue import AbortGlue


DEFAULT_HANDLER = """
__attribute__((naked, noreturn))
void %(name)s(void) {
    while (1) {}
}
"""

@runtimes.runtime
class ARMv7MSysRuntime(ErrorGlue, WriteGlue, AbortGlue, runtimes.Runtime):
    """
    A bento-box runtime that runs in privledge mode on the system.
    Usually required at the root of the project.
    """
    __argname__ = "armv7m_sys"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser, **kwargs):
        parser.add_argument('--no_startup', type=bool,
            help="Don't emit startup code and isr_vector used to "
                "initialize the device.")
        parser.add_nestedparser('--isr_vector', Section)

    def __init__(self, no_startup=None, isr_vector=None):
        super().__init__()
        self._no_startup = no_startup or False
        self._isr_vector = Section('isr_vector', **{**isr_vector.__dict__,
            'size': isr_vector.size
                if isr_vector.size is not None else
                0x400})

    __name = __argname__
    def box(self, box):
        if not box.stack.size:
            print("warning: Box `%s` has no stack!" % box.name)
        super().box(box)
        self._isr_vector.alloc(box, 'rp')

        if not self._no_startup:
            # allow overloading main, but default to using main if available
            self._main_hook = box.addimport(
                '__box_main', 'fn() -> void',
                scope=box.name, source=self.__name, weak=True,
                doc="Entry point to the program. By default this will be "
                    "hooked up to call the normal C main.")

            # link isr vector entries
            self._esr_hooks = [
                box.addimport('__box_nmi_handler', 'fn() -> void',
                    scope=box.name, source=self.__name, weak=True),
                box.addimport('__box_hardfault_handler', 'fn() -> void',
                    scope=box.name, source=self.__name, weak=True),
                box.addimport('__box_memmanage_handler', 'fn() -> void',
                    scope=box.name, source=self.__name, weak=True),
                box.addimport('__box_busfault_handler', 'fn() -> void',
                    scope=box.name, source=self.__name, weak=True),
                box.addimport('__box_usagefault_handler', 'fn() -> void',
                    scope=box.name, source=self.__name, weak=True),
                None,
                None,
                None,
                None,
                box.addimport('__box_svc_handler', 'fn() -> void',
                    scope=box.name, source=self.__name, weak=True),
                box.addimport('__box_debugmon_handler', 'fn() -> void',
                    scope=box.name, source=self.__name, weak=True),
                None,
                box.addimport('__box_pendsv_handler', 'fn() -> void',
                    scope=box.name, source=self.__name, weak=True),
                box.addimport('__box_systick_handler', 'fn() -> void',
                    scope=box.name, source=self.__name, weak=True),
            ]

            self._isr_hooks = []
            for i in range(self._isr_vector.size//4 - 16):
                self._isr_hooks.append(box.addimport(
                    '__box_irq%d_handler' % i, 'fn() -> void',
                    scope=box.name, source=self.__name, weak=True))

    def build_ld(self, output, box):
        # reset handler
        output.decls.append('ENTRY(__box_reset_handler)')

        # interrupt vector
        if self._isr_vector:
            out = output.sections.append(
                section='.isr_vector',
                memory=self._isr_vector.memory.name)
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__isr_vector_start = .;')
            out.printf('.isr_vector . : {')
            with out.pushindent():
                out.printf('KEEP(*(.isr_vector))')
                out.printf('. = __isr_vector_start + %(isr_vector_size)#x;',
                    isr_vector_size=self._isr_vector.size)
            out.printf('} > %(MEMORY)s')
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__isr_vector_end = .;')

        super().build_ld(output, box)

    def build_c(self, output, box):
        super().build_c(output, box)

        # default write/abort hooks
        if not self._no_startup:
            output.decls.append('//// ISR Vector definitions ////')

            # default to standard main definition
            if not self._main_hook.link:
                output.decls.append('extern void main(void);')

            # create entry point
            out = output.decls.append(doc='Reset Handler')
            out.printf('__attribute__((naked, noreturn))')
            out.printf('int32_t __box_reset_handler(void) {')
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
                out.printf('// enter main')
                out.printf('%(main)s();',
                    main=self._main_hook.link.export.alias
                        if self._main_hook.link else 'main')
                out.printf()
                out.printf('// halt if main exits')
                out.printf('while (1) {')
                with out.indent():
                    out.printf('__asm__ volatile ("wfi");')
                out.printf('}')
            out.printf('}')

            # create default isrs, we have the standard ARM isrs
            # declared to help with debugging
            output.decls.append('//// Default handlers ////')
            for esr in self._esr_hooks:
                if esr and not esr.link:
                    output.decls.append(DEFAULT_HANDLER,
                        name=esr.alias)
                        
            output.decls.append(DEFAULT_HANDLER,
                name='__box_default_handler')

            # forward declare internal exports as needed
            out = output.decls.append()
            for handler in it.chain(self._esr_hooks, self._isr_hooks):
                if (handler and handler.link and
                        handler.link.export.source != box.name):
                    out.printf('void %(name)s(void);', name=handler.alias)

            output.decls.append('extern uint32_t __stack_end;')

            # now create actual vector table
            output.decls.append('//// ISR Vector ////')
            out = output.decls.append(
                size=2+len(self._esr_hooks)+len(self._isr_hooks))
            out.printf('__attribute__((used, section(".isr_vector")))')
            out.printf('const uint32_t __isr_vector[%(size)d] = {')
            with out.indent():
                out.printf('(uint32_t)&__stack_end,')
                out.printf('(uint32_t)&__box_reset_handler,')
                out.printf('// Exception handlers')
                for esr in self._esr_hooks:
                    out.printf('(uint32_t)%(handler)s,', handler=
                        0
                        if not esr else
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
