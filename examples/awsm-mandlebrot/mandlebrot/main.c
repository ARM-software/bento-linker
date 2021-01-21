/*
 * Bento-linker example
 *
 * Copyright (c) 2020, Arm Limited. All rights reserved.
 * SPDX-License-Identifier: BSD-3-Clause
 */

#include "bb.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void generate(uint8_t *image, size_t w, size_t h, int iterations) {
    float limit = 2.0;
    float Zr, Zi, Cr, Ci, Tr, Ti;

    for (float y = 0; y < h; y++) {
        for (float x = 0; x < w; x++) {
            Zr = Zi = Tr = Ti = 0.0;
            Cr = (2.0*x/w - 1.5); Ci=(2.0*y/h - 1.0);

            int i;
            for (i = 0; i < iterations && (Tr+Ti <= limit*limit); i++) {
                Zi = 2.0*Zr*Zi + Ci;
                Zr = Tr - Ti + Cr;
                Tr = Zr * Zr;
                Ti = Zi * Zi;
            }

            image[(int)x+(int)y*w] = i;
        }
    }
}

const char shades[8] = "#%x=-.  ";

uint32_t npw2(uint32_t x) {
    return 32 - __builtin_clz(x-1);
}

int mandlebrot(size_t w, size_t h, uint32_t iterations) {
    uint8_t *image = malloc(w * h);
    memset(image, 0, w*h);

    generate(image, w, h, iterations);

    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            printf("%c", shades[npw2(image[x+y*w])-1]);
            if (x == w-1) {
                printf("\n");
            }
        }
    }

    free(image);
    return 0;
}
