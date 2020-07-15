#include "bb.h"
#include <stdio.h>

int32_t boxc_add2(int32_t a, int32_t b) {
    return a + b;
}

int boxc_hello(void) {
    printf("Hello from C!\n");
    return 0;
}

static uint8_t buffer[64];
void *boxc_qsort_alloc(size_t size) {
    if (size > sizeof(buffer)) {
        return NULL;
    }

    return buffer;
}

ssize_t boxc_qsort_partition(uint32_t *buffer, size_t size, uint32_t pivot) {
    int i = 0;
    for (int j = 0; j < size; j++) {
        if (buffer[j] < pivot) {
            uint32_t x = buffer[j];
            buffer[j] = buffer[i];
            buffer[i] = x;
            i += 1;
        }
    }

    return i;
}

int boxc_qsort(uint32_t *buffer, size_t size) {
    if (size == 0) {
        return 0;
    }

    uint32_t pivot = buffer[size-1];
    int i = boxc_qsort_partition(buffer, size-1, pivot);
    if (i < 0) {
        return i;
    }

    uint32_t x = buffer[size-1];
    buffer[size-1] = buffer[i];
    buffer[i] = x;

    int err = boxc_qsort(buffer, i);
    if (err) {
        return err;
    }
    err = boxc_qsort(buffer+(i+1), size-(i+1));
    if (err) {
        return err;
    }

    return 0;
}
