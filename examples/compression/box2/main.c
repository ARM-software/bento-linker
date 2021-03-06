/*
 * Bento-linker example
 *
 * Copyright (c) 2020, Arm Limited. All rights reserved.
 * SPDX-License-Identifier: BSD-3-Clause
 */

#include "bb.h"
#include <stdio.h>

int32_t box2_add2(int32_t a, int32_t b) {
    return a + b;
}

int box2_hello(void) {
    printf("box2 says hello!\n");
    return 0;
}
