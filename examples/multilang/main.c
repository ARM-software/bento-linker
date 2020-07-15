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

static int qsort(
        int (*const *partitions)(
            uint32_t *buffer, size_t size, uint32_t pivot),
        int i, int count,
        uint32_t *const *buffers, size_t off, size_t size) {
    if (size == 0) {
        return 0;
    }

    // partition
    uint32_t pivot = buffers[i][off+size-1];
    ssize_t j = partitions[i](buffers[i]+off, size-1, pivot);
    if (j < 0) {
        return j;
    }

    // swap
    uint32_t x = buffers[i][off+size-1];
    buffers[i][off+size-1] = buffers[i][off+j];
    buffers[i][off+j] = x;

    // switch partitioner
    int ni = (i + 1) % count;
    memcpy(buffers[ni]+off, buffers[i]+off, size*sizeof(uint32_t));

    // recurse
    int err = qsort(partitions, ni, count, buffers, off, j);
    if (err) {
        return err;
    }

    err = qsort(partitions, ni, count, buffers, off+(j+1), size-(j+1));
    if (err) {
        return err;
    }

    return 0;
}

void main(void) {
    nrfx_err_t err = nrfx_uarte_init(&uart, &uart_config, NULL);
    assert(err == NRFX_SUCCESS);
    (void)err;

    printf("hi from nrf52840!\n");

    printf("pinging boxc\n");
    int32_t x = boxc_add2(1, 2);
    printf("1 + 2 = %d\n", x);

    printf("pinging boxrust\n");
    x = boxrust_add2(1, 2);
    printf("1 + 2 = %d\n", x);

    printf("testing printf\n");
    int x1 = boxc_hello();
    int x2 = boxrust_hello();
    printf("return values: %d %d\n", x1, x2);

    printf("testing boxc qsort\n");
    uint32_t *boxc_buffer = boxc_qsort_alloc(10*sizeof(uint32_t));
    // "random"
    memcpy(boxc_buffer,
            (uint32_t[]){9,4,7,5,1,2,6,3,8,0},
            10*sizeof(uint32_t));
    int res = boxc_qsort(boxc_buffer, 10);
    printf("result: %d\n", res);
    printf("qsort: [");
    for (int i = 0; i < 10; i++) {
        printf("%d%s", boxc_buffer[i], (i < 10-1) ? ", " : "");
    }
    printf("]\n");

    printf("testing boxrust qsort\n");
    uint32_t *boxrust_buffer = boxrust_qsort_alloc(10*sizeof(uint32_t));
    // "random"
    memcpy(boxrust_buffer,
            (uint32_t[]){9,4,7,5,1,2,6,3,8,0},
            10*sizeof(uint32_t));
    res = boxrust_qsort(boxrust_buffer, 10);
    printf("result: %d\n", res);
    printf("qsort: [");
    for (int i = 0; i < 10; i++) {
        printf("%d%s", boxrust_buffer[i], (i < 10-1) ? ", " : "");
    }
    printf("]\n");

    printf("testing qsort where we switch languages for every partition\n");
    memcpy(boxc_buffer,
            (uint32_t[]){9,4,7,5,1,2,6,3,8,0},
            10*sizeof(uint32_t));
    res = qsort(
            (int (*const[])(uint32_t *buffer, size_t size, uint32_t pivot)){
                boxc_qsort_partition,
                boxrust_qsort_partition},
            0, 2,
            (uint32_t *const[]){
                boxc_buffer,
                boxrust_buffer},
            0, 10);
    printf("result: %d\n", res);
    printf("qsort: [");
    for (int i = 0; i < 10; i++) {
        printf("%d%s", boxc_buffer[i], (i < 10-1) ? ", " : "");
    }
    printf("]\n");

    printf("done\n");
}
