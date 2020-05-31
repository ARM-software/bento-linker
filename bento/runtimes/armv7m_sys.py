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
        "ldr r0, =main \\n\\t"
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
        super().box_box(box)

    # overidable
    def build_reset_handler(self, output, box):
        output.decls.append(RESET_HANDLER)

    def build_box_ld(self, output, box):
        # reset handler
        output.decls.append('ENTRY(Reset_Handler)')

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
        if self._no_startup:
            # don't emit this then
            return

        # TODO configure these elsewhere?
        # TODO configure irqs or use different names, these are non-standard
        exceptions = [
            'NMI_Handler',
            'HardFault_Handler',
            'MemManage_Handler',
            'BusFault_Handler',
            'UsageFault_Handler',
            None,
            None,
            None,
            None,
            'SVC_Handler',
            'DebugMon_Handler',
            None,
            'PendSV_Handler',
            'SysTick_Handler']
        irqs = [
            'POWER_CLOCK_IRQHandler',
            'RADIO_IRQHandler',
            'UARTE0_UART0_IRQHandler',
            'SPIM0_SPIS0_TWIM0_TWIS0_SPI0_TWI0_IRQHandler',
            'SPIM1_SPIS1_TWIM1_TWIS1_SPI1_TWI1_IRQHandler',
            'NFCT_IRQHandler',
            'GPIOTE_IRQHandler',
            'SAADC_IRQHandler',
            'TIMER0_IRQHandler',
            'TIMER1_IRQHandler',
            'TIMER2_IRQHandler',
            'RTC0_IRQHandler',
            'TEMP_IRQHandler',
            'RNG_IRQHandler',
            'ECB_IRQHandler',
            'CCM_AAR_IRQHandler',
            'WDT_IRQHandler',
            'RTC1_IRQHandler',
            'QDEC_IRQHandler',
            'COMP_LPCOMP_IRQHandler',
            'SWI0_EGU0_IRQHandler',
            'SWI1_EGU1_IRQHandler',
            'SWI2_EGU2_IRQHandler',
            'SWI3_EGU3_IRQHandler',
            'SWI4_EGU4_IRQHandler',
            'SWI5_EGU5_IRQHandler',
            'TIMER3_IRQHandler',
            'TIMER4_IRQHandler',
            'PWM0_IRQHandler',
            'PDM_IRQHandler',
            None,
            None,
            'MWU_IRQHandler',
            'PWM1_IRQHandler',
            'PWM2_IRQHandler',
            'SPIM2_SPIS2_SPI2_IRQHandler',
            'RTC2_IRQHandler',
            'I2S_IRQHandler',
            'FPU_IRQHandler',
            'USBD_IRQHandler',
            'UARTE1_IRQHandler',
            'QSPI_IRQHandler',
            'CRYPTOCELL_IRQHandler',
            None,
            None,
            'PWM3_IRQHandler',
            None,
            'SPIM3_IRQHandler',
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None]

        output.decls.append('//// ISR Vector definitions ////')

        # create entry point
        output.decls.append(RESET_HANDLER,
            name='Reset_Handler',
            doc='Reset Handler')

        # create default handler stubs, we use a separate function
        # for each to aid with debugging unassigned handlers

        # exceptions
        for i, name in enumerate(exceptions):
            if not name:
                continue
            # TODO hack to avoid conflicts with MPU
            if (any(child.runtime == 'armv7m_mpu' for child in box.boxes) and
                    name in {
                        'UsageFault_Handler',
                        'BusFault_Handler',
                        'MemManage_Handler'}):
                output.decls.append('void %(name)s(void);', name=name)
                continue
            output.decls.append(DEFAULT_HANDLER,
                name=name,
                doc='Exceptions' if i == 0 else None)

        # irqs
        for i, name in enumerate(irqs):
            if not name:
                continue
            output.decls.append(DEFAULT_HANDLER,
                name=name,
                doc='External IRQs' if i == 0 else None)

        # now we create the actual vector table (needed the predeclared)
        output.decls.append('//// ISR Vector ////')
        output.decls.append('extern uint32_t __stack_end;')
        out = output.decls.append()
        out.printf('__attribute__((section(".isr_vector")))')
        out.printf('const uint32_t __isr_vector[%(size)d] = {',
            size = 2+len(exceptions)+len(irqs))
        with out.indent():
            out.printf('(uint32_t)&__stack_end,')
            for name in it.chain(['Reset_Handler'], exceptions, irqs):
                if name:
                    out.printf('(uint32_t)%(name)s,', name=name)
                else:
                    out.printf('0,')
        out.printf('};')

