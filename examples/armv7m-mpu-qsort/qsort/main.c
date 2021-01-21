/*
 * Bento-linker example
 *
 * Copyright (c) 2020, Arm Limited. All rights reserved.
 * SPDX-License-Identifier: BSD-3-Clause
 */

#include "bb.h"
#include <stdio.h>
#include <stdlib.h>

static int box_partition(
        uint32_t *buffer, size_t size, uint32_t pivot) {
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

int box_qsort(uint32_t *buffer, size_t size) {
    if (size == 0) {
        return 0;
    }

    uint32_t pivot = buffer[size-1];
    int i = box_partition(buffer, size-1, pivot);
    uint32_t x = buffer[size-1];
    buffer[size-1] = buffer[i];
    buffer[i] = x;

    box_qsort(buffer, i);
    box_qsort(buffer+(i+1), size-(i+1));
    return 0;
}
