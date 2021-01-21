/*
 * Bento-linker example
 *
 * Copyright (c) 2020, Arm Limited. All rights reserved.
 * SPDX-License-Identifier: BSD-3-Clause
 */

#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <nrfx_uarte.h>
#include "bb.h"

#ifndef SYS_KEY_COUNT
#define SYS_KEY_COUNT 4
#endif

#ifndef SYS_KEY_SIZE
#define SYS_KEY_SIZE 1024
#endif

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

// entropy
ssize_t sys_entropy_poll(void *pbuffer, size_t size) {
    uint8_t *buffer = pbuffer;

    // wow such entropy
    // TODO hook this into nrfx?
    for (int i = 0; i < size; i++) {
        buffer[i] = i;
    }

    return size;
}

// TLS bindings
static int32_t keys[2][SYS_KEY_COUNT];

static int32_t sys_setkey(int32_t box, int32_t key) {
    if (key < 0) {
        return key;
    }

    for (int i = 0; i < SYS_KEY_COUNT; i++) {
        if (keys[box][i] == 0) {
            keys[box][i] = key;
            return i+1;
        }
    }

    return -ENOMEM;
}

static int32_t sys_getkey(int32_t box, int32_t key) {
    if (key-1 >= 0 && key-1 < SYS_KEY_COUNT) {
        return keys[box][key-1];
    }

    return -EINVAL;
}

static int32_t sys_delkey(int32_t box, int32_t key) {
    if (key-1 >= 0 && key-1 < SYS_KEY_COUNT) {
        int32_t nkey = keys[box][key-1];
        keys[box][key-1] = 0;
        return nkey;
    }

    return -EINVAL;
}

int32_t sys_rsa_genkey(int32_t box, size_t key_size, int32_t exponent) {
    return sys_setkey(box, tlsbox_rsa_genkey(key_size, exponent));
}

int sys_rsa_freekey(int32_t box, int32_t key) {
    return tlsbox_rsa_freekey(sys_delkey(box, key));
}

int sys_rsa_getpubkey(int32_t box, int32_t key,
        char *buffer, size_t size) {
    char *tlsbuffer = __box_tlsbox_push(size);
    if (!tlsbuffer) {
        return -ENOMEM;
    }

    int err = tlsbox_rsa_getpubkey(
            sys_getkey(box, key), tlsbuffer, size);
    if (err) {
        __box_tlsbox_pop(size);
        return err;
    }

    strcpy(buffer, tlsbuffer);
    __box_tlsbox_pop(size);
    return 0;
}

int sys_rsa_getprivkey(int32_t box, int32_t key,
        char *buffer, size_t size) {
    char *tlsbuffer = __box_tlsbox_push(size);
    if (!tlsbuffer) {
        return -ENOMEM;
    }

    int err = tlsbox_rsa_getprivkey(
            sys_getkey(box, key), tlsbuffer, size);
    if (err) {
        __box_tlsbox_pop(size);
        return err;
    }

    strcpy(buffer, tlsbuffer);
    __box_tlsbox_pop(size);
    return 0;
}

int32_t sys_rsa_frompubkey(int32_t box,
        const char *buffer, size_t size) {
    char *tlsbuffer = __box_tlsbox_push(size);
    if (!tlsbuffer) {
        return -ENOMEM;
    }

    memcpy(tlsbuffer, buffer, size);
    int32_t key = sys_setkey(box, tlsbox_rsa_frompubkey(tlsbuffer, size));
    __box_tlsbox_pop(size);
    return key;
}

int32_t sys_rsa_fromprivkey(int32_t box,
        const char *buffer, size_t size) {
    char *tlsbuffer = __box_tlsbox_push(size);
    if (!tlsbuffer) {
        return -ENOMEM;
    }

    memcpy(tlsbuffer, buffer, size);
    int32_t key = sys_setkey(box, tlsbox_rsa_fromprivkey(tlsbuffer, size));
    __box_tlsbox_pop(size);
    return key;
}

int sys_rsa_pkcs1_encrypt(int32_t box, int32_t key,
        const void *input, size_t input_size, void *output) {
    char *tlsbuffer = __box_tlsbox_push(input_size + SYS_KEY_SIZE/8);
    if (!tlsbuffer) {
        return -ENOMEM;
    }

    memcpy(tlsbuffer, input, input_size);
    int err = tlsbox_rsa_pkcs1_encrypt(
            sys_getkey(box, key),
            tlsbuffer, input_size,
            tlsbuffer+input_size);
    if (err) {
        __box_tlsbox_pop(input_size + SYS_KEY_SIZE/8);
        return err;
    }

    memcpy(output, tlsbuffer+input_size, SYS_KEY_SIZE/8);
    __box_tlsbox_pop(input_size + SYS_KEY_SIZE/8);
    return 0;
}

ssize_t sys_rsa_pkcs1_decrypt(int32_t box, int32_t key,
        const void *input, void *output, size_t output_size) {
    char *tlsbuffer = __box_tlsbox_push(SYS_KEY_SIZE/8 + output_size);
    if (!tlsbuffer) {
        return -ENOMEM;
    }

    memcpy(tlsbuffer, input, SYS_KEY_SIZE/8);
    ssize_t res = tlsbox_rsa_pkcs1_decrypt(
            sys_getkey(box, key),
            tlsbuffer,
            tlsbuffer+SYS_KEY_SIZE/8, output_size);
    if (res < 0) {
        __box_tlsbox_pop(SYS_KEY_SIZE/8 + output_size);
        return res;
    }

    memcpy(output, tlsbuffer+SYS_KEY_SIZE/8, res);
    __box_tlsbox_pop(SYS_KEY_SIZE/8 + output_size);
    return res;
}

// alice/bob bindings
int bobbox_alicebox_getpubkey(char *buffer, size_t size) {
    char *alicebuffer = __box_alicebox_push(size);
    if (!alicebuffer) {
        return -ENOMEM;
    }

    int err = alicebox_getpubkey(alicebuffer, size);
    if (err) {
        __box_alicebox_pop(size);
        return err;
    }

    memcpy(buffer, alicebuffer, size);
    __box_alicebox_pop(size);
    return 0;
}

int alicebox_bobbox_getpubkey(char *buffer, size_t size) {
    char *bobbuffer = __box_bobbox_push(size);
    if (!bobbuffer) {
        return -ENOMEM;
    }

    int err = bobbox_getpubkey(bobbuffer, size);
    if (err) {
        __box_bobbox_pop(size);
        return err;
    }

    memcpy(buffer, bobbuffer, size);
    __box_bobbox_pop(size);
    return 0;
}

int sys_send_to_alice(const void *buffer, size_t size) {
    char *alicebuffer = __box_alicebox_push(size);
    if (!alicebuffer) {
        return -ENOMEM;
    }

    memcpy(alicebuffer, buffer, size);
    int err = alicebox_recv(alicebuffer, size);
    __box_alicebox_pop(size);
    return err;
}

int sys_send_to_bob(const void *buffer, size_t size) {
    char *bobbuffer = __box_bobbox_push(size);
    if (!bobbuffer) {
        return -ENOMEM;
    }

    memcpy(bobbuffer, buffer, size);
    int err = bobbox_recv(bobbuffer, size);
    if (err) {
        __box_bobbox_pop(size);
        return err;
    }

    __box_bobbox_pop(size);
    return 0;
}


// entry point
void main(void) {
    nrfx_err_t err = nrfx_uarte_init(&uart, &uart_config, NULL);
    assert(err == NRFX_SUCCESS);
    (void)err;

    printf("sys: hi from nrf52840!\n");

    printf("sys: seeding drbg...\n");
    int res = tlsbox_drbg_seed();
    printf("sys: result: %d\n", res);

    printf("sys: initializing boxes...\n");
    int x1 = bobbox_init();
    int x2 = alicebox_init();
    printf("sys: results: %d %d\n", x1, x2);

    // measuring key generation isn't really useful as it involves
    // polling for sufficiently large numbers, so we start profiling
    // here
    cyccnt_init();
    uint32_t cyccnt = cyccnt_read();

    printf("sys: calling alicebox_main...\n");
    res = alicebox_main();
    printf("sys: result: %d\n", res);

    printf("sys: calling bobbox_main...\n");
    res = bobbox_main();
    printf("sys: result: %d\n", res);

    // log cycles
    cyccnt = cyccnt_read() - cyccnt;
    printf("sys: %u cycles\n", cyccnt);

    // log ram usage, and then mark it for the next run
    uint32_t *ram_start = (uint32_t*)0x20000000;
    uint32_t *ram_end   = (uint32_t*)0x20040000;

    uint32_t ram_usage = 0;
    for (uint32_t *p = ram_start; p < ram_end; p++) {
        if (*p != 0xcccccccc) {
            ram_usage += 4;
        }
    }
    printf("sys: %u bytes ram\n", ram_usage);

    for (uint32_t *p = ram_start; p < ram_end; p++) {
        *p = 0xcccccccc;
    }
}
