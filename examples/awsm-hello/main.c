#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <nrfx_uarte.h>
#include "bb.h"

// uart hooks for nrfx
nrfx_uarte_t uart = {
    .p_reg = NRF_UARTE0,
    .drv_inst_idx = NRFX_UARTE0_INST_IDX,
};
const nrfx_uarte_config_t uart_config = {
    .pseltxd = 6,
    .pselrxd = 8,
    .pselcts = NRF_UARTE_PSEL_DISCONNECTED,
    .pselrts = NRF_UARTE_PSEL_DISCONNECTED,
    .p_context = NULL,
    .baudrate = NRF_UARTE_BAUDRATE_115200,
    .interrupt_priority = NRFX_UARTE_DEFAULT_CONFIG_IRQ_PRIORITY,
    .hal_cfg = {
        .hwfc = NRF_UARTE_HWFC_DISABLED,
        .parity = NRF_UARTE_PARITY_EXCLUDED,
        NRFX_UARTE_DEFAULT_EXTENDED_STOP_CONFIG
        NRFX_UARTE_DEFAULT_EXTENDED_PARITYTYPE_CONFIG
    }
};

// stdout hook
ssize_t __box_write(int32_t handle, const void *p, size_t size) {
    // stdout or stderr only
    assert(handle == 1 || handle == 2);
    const char *buffer = p;

    int i = 0;
    while (true) {
        char *nl = memchr(&buffer[i], '\n', size-i);
        int span = nl ? nl-&buffer[i] : size-i;
        if ((uint32_t)buffer < 0x2000000) {
            // special case for flash
            for (int j = 0; j < span; j++) {
                char c = buffer[i+j];
                nrfx_err_t err = nrfx_uarte_tx(&uart, (uint8_t*)&c, 1);
                assert(err == NRFX_SUCCESS);
                (void)err;
            }
        } else { 
            nrfx_err_t err = nrfx_uarte_tx(&uart, (uint8_t*)&buffer[i], span);
            assert(err == NRFX_SUCCESS);
            (void)err;
        } 
        i += span;

        if (i >= size) {
            return size;
        }

        char r[2] = "\r\n";
        nrfx_err_t err = nrfx_uarte_tx(&uart, (uint8_t*)r, sizeof(r));
        assert(err == NRFX_SUCCESS);
        (void)err;
        i += 1;
    }
}

// measure cycle counts
#define DEMCR      ((volatile uint32_t*)0xe000edfc)
#define DWT_CTRL   ((volatile uint32_t*)0xe0001000)
#define DWT_CYCCNT ((volatile uint32_t*)0xe0001004)
int cyccnt_init(void) {
    // enable DWT
    *DEMCR |= 0x01000000;
    // enable CYCCNT
    *DWT_CTRL |= 0x00000001;
    return 0;
}

__attribute__((always_inline))
static inline uint32_t cyccnt_read(void) {
    return *DWT_CYCCNT;
}

// used to debug box imports
int32_t sys_ping(int32_t a) {
    return a + 3;
}

void main(void) {
    nrfx_err_t err = nrfx_uarte_init(&uart, &uart_config, NULL);
    assert(err == NRFX_SUCCESS);
    (void)err;

    cyccnt_init();
    uint32_t cyccnt = cyccnt_read();

    printf("hi from nrf52840!\n");

    int32_t x1, x2, x3;
    printf("testing box ping\n");
    x1 = box1_ping(0);
    x2 = box2_ping(0);
    x3 = box3_ping(0);
    printf("results: %d %d %d\n", x1, x2, x3);

    printf("testing box import ping\n");
    x1 = box1_ping_import(0);
    x2 = box2_ping_import(0);
    x3 = box3_ping_import(0);
    printf("results: %d %d %d\n", x1, x2, x3);

    printf("testing box abort ping\n");
    x1 = box1_ping_abort(0);
    x2 = box2_ping_abort(0);
    x3 = box3_ping_abort(0);
    printf("results: %d %d %d\n", x1, x2, x3);

    printf("testing box printf\n");
    x1 = box1_hello();
    x2 = box2_hello();
    x3 = box3_hello();
    printf("return values: %d %d %d\n", x1, x2, x3);

    printf("done\n");

    // log cycles
    cyccnt = cyccnt_read() - cyccnt;
    printf("sys: %u cycles\n", cyccnt);

    // log ram usage, and then mark it for the next run
    uint32_t *ram_start = (uint32_t*)0x20000000;
    uint32_t *ram_end   = (uint32_t*)0x20040000;

    uint32_t ram_usage = 0;
    for (uint32_t *p = ram_start; p < ram_end; p++) {
        if (*p != 0x00000000) {
            ram_usage += 4;
        }
    }
    printf("sys: %u bytes ram\n", ram_usage);

    for (uint32_t *p = ram_start; p < ram_end; p++) {
        *p = 0x00000000;
    }
}
