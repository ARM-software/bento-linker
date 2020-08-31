#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <nrfx_uarte.h>
#include <nrfx_clock.h>
#include <nrfx_timer.h>
#include "bb.h"

void bench_start(void);
void bench_stop(void);

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
    bench_stop();

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
            bench_start();
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

// measurement for benchmarking
uint64_t bench_value = 0;
int bench_startedyet = 0;
void bench_start(void) {
    bench_startedyet += 1;
    if (bench_startedyet > 0) {
        bench_value -= timer_getns();
    }
}

void bench_stop(void) {
    if (bench_startedyet > 0) {
        bench_value += timer_getns();
    }
    bench_startedyet -= 1;
}


// littlefs test operations
void do_boot_count(uint8_t *buffer, size_t size) {
    strcpy((char*)buffer, "boot_count");
    int32_t fd = lfsbox_file_open((char*)buffer, 0x0103);
    assert(fd >= 0 || fd == -ENOENT);
    
    uint32_t boot_count = 0;
    ssize_t res = lfsbox_file_read(fd, buffer, sizeof(uint32_t));
    assert(res >= 0);
    memcpy(&boot_count, buffer, res);

    printf("sys: boot_count = %d\n", boot_count);
    boot_count += 1;

    int err = lfsbox_file_seek(fd, 0, 0);
    assert(!err);

    memcpy(buffer, &boot_count, sizeof(uint32_t));
    res = lfsbox_file_write(fd, buffer, sizeof(uint32_t));
    assert(res == sizeof(uint32_t));

    err = lfsbox_file_close(fd);
    assert(!err);
}

void do_log_log(uint8_t *buffer, size_t size, int iterations) {
    uint32_t value = 0x12341234;

    // read most recent value from rotated log
    strcpy((char*)buffer, "log.0");
    int32_t fd = lfsbox_file_open((char*)buffer, 0x0001);
    assert(fd >= 0 || fd == -ENOENT);
    if (fd != -ENOENT) {
        int32_t res = lfsbox_file_seek(fd, -4, 2);
        assert(res >= 0 || res == -EINVAL);
        res = lfsbox_file_read(fd, buffer, sizeof(uint32_t));
        assert(res >= 0);
        memcpy(&value, buffer, res);

        printf("sys: log value = 0x%08x\n", value);

        int err = lfsbox_file_close(fd);
        assert(!err);
    }

    // create new log
    strcpy((char*)buffer, "log");
    fd = lfsbox_file_open((char*)buffer, 0x0902);
    assert(fd >= 0);

    for (int i = 0; i < iterations; i++) {
        // append new value to log
        value = (value << 1) | (value >> 31);

        memcpy(buffer, &value, sizeof(uint32_t));
        int32_t res = lfsbox_file_write(fd, buffer, sizeof(uint32_t));
        assert(res == sizeof(uint32_t));
    }

    int err = lfsbox_file_close(fd);
    assert(!err);
}

void do_log_rotate(uint8_t *buffer, size_t size) {
    printf("sys: log rotating...\n");
    char *path1 = (char*)buffer;
    char *path2 = (char*)buffer + size/2;
    strcpy(path1, "log");
    strcpy(path2, "log.0");
    int err = lfsbox_rename(path1, path2);
    assert(!err);
}

// entry point
void main(void) {
    nrfx_err_t nerr;
    // setup LCLK
    nerr = nrfx_clock_init(clock_handler);
    (void)nerr; assert(nerr == NRFX_SUCCESS);
    nrfx_clock_start(NRF_CLOCK_DOMAIN_LFCLK);

    // setup UART
    nerr = nrfx_uarte_init(&uart, &uart_config, NULL);
    (void)nerr; assert(nerr == NRFX_SUCCESS);

    // setup TIMER0
    nerr = nrfx_timer_init(&timer0, &timer0_config, &timer0_handler);
    (void)nerr; assert(nerr == NRFX_SUCCESS);
    nrfx_timer_extended_compare(&timer0, NRF_TIMER_CC_CHANNEL0,
        nrfx_timer_ms_to_ticks(&timer0, 1000),
        NRF_TIMER_SHORT_COMPARE0_CLEAR_MASK, true);
    nrfx_timer_enable(&timer0);

    printf("hi from nrf52840!\n");
    bench_start();

    int err = lfsbox_format();
    printf("lfsbox_format: %d\n", err);
    assert(!err);

    for (int i = 0; i < 10; i++) {
        // reset state
        // don't count takedown cost, in theory we lost power
        bench_stop();
        __box_lfsbox_clobber();
        bench_start();
        __box_lfsbox_init();
        uint8_t *buffer = __box_lfsbox_push(128);
        assert(buffer);

        err = lfsbox_mount();
        printf("lfsbox_mount: %d\n", err);
        assert(!err);

        do_boot_count(buffer, 128);
        for (int i = 0; i < 10; i++) {
            do_log_log(buffer, 128, 1000);
            do_log_rotate(buffer, 128);
        }

        err = lfsbox_mount();
        printf("lfsbox_unmount: %d\n", err);
        assert(!err);
    }

    bench_stop();
    printf("done\n");

    // log cycles
    if (bench_value >> 32) {
        printf("sys: %u*(2^32) + %u ns\n",
            (uint32_t)(bench_value >> 32), (uint32_t)bench_value);
    } else {
        printf("sys: %u ns\n", (uint32_t)bench_value);
    }

    // remove block device from RAM measurement
    extern int bd_eraseall(void);
    bd_eraseall();

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
