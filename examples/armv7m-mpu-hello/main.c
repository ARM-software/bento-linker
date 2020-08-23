#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <nrfx_uarte.h>
#include <nrfx_clock.h>
#include <nrfx_timer.h>
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
        if (span == 0) {
            // pass
        } else if ((uint32_t)buffer < 0x2000000) {
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


// timer hooks for nrfx
nrfx_timer_t timer0 = {
    .p_reg = NRF_TIMER0,
    .instance_id = NRFX_TIMER0_INST_IDX,
    .cc_channel_count = 4,
};
const nrfx_timer_config_t timer0_config = {
    .frequency = NRF_TIMER_FREQ_1MHz,
    .mode = NRF_TIMER_MODE_TIMER,
    .bit_width = NRF_TIMER_BIT_WIDTH_32,
    .interrupt_priority = NRFX_TIMER_DEFAULT_CONFIG_IRQ_PRIORITY,
    .p_context = NULL,
};

// timing things
void clock_handler(nrfx_clock_evt_type_t event) {
}

uint64_t timer_hi = 0;
void timer0_handler(nrf_timer_event_t event, void *p) {
    timer_hi += 1000000;
}

uint64_t timer_getns(void) {
    return timer_hi + nrfx_timer_capture(&timer0, NRF_TIMER_CC_CHANNEL1);
}


// used to debug box imports
int32_t sys_ping(int32_t a) {
    return a + 3;
}

void main(void) {
    nrfx_err_t err;
    // setup LCLK
    err = nrfx_clock_init(clock_handler);
    (void)err; assert(err == NRFX_SUCCESS);
    nrfx_clock_start(NRF_CLOCK_DOMAIN_LFCLK);

    // setup UART
    err = nrfx_uarte_init(&uart, &uart_config, NULL);
    (void)err; assert(err == NRFX_SUCCESS);

    // setup TIMER0
    err = nrfx_timer_init(&timer0, &timer0_config, &timer0_handler);
    (void)err; assert(err == NRFX_SUCCESS);
    nrfx_timer_extended_compare(&timer0, NRF_TIMER_CC_CHANNEL0,
        nrfx_timer_ms_to_ticks(&timer0, 1000),
        NRF_TIMER_SHORT_COMPARE0_CLEAR_MASK, true);
    nrfx_timer_enable(&timer0);

    printf("hi from nrf52840!\n");
    uint64_t start = timer_getns();

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

    uint64_t stop = timer_getns();
    printf("done\n");

    // log cycles
    uint64_t time = stop - start;
    if (time >> 32) {
        printf("sys: %u*(2^32) + %u ns\n",
            (uint32_t)(time >> 32), (uint32_t)time);
    } else {
        printf("sys: %u ns\n", (uint32_t)time);
    }

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
