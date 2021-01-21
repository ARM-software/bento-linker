/*
 * Minimal implementation of a GLZ decoder, operates in
 * constant RAM and linear time.
 *
 * This version uses both a write callback for output, and
 * read/seek callbacks for input. This isn't the most efficient
 * implementation but at least proves the feasibility.
 *
 * Copyright (c) 2020, Arm Limited. All rights reserved.
 * SPDX-License-Identifier: BSD-3-Clause
 *
 */
#include <sys/types.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdlib.h>

#include <stdio.h>
#include <errno.h>
#include <sys/stat.h>
#include <sys/mman.h>


// types and GLZ's M constant (width of reference nibbles)
#ifndef GLZ_M
#define GLZ_M 4
#endif

enum glz_error {
    GLZ_ERR_OK     = 0,     // No error
    GLZ_ERR_INVAL  = -22,   // Invalid
};

typedef uint32_t glz_off_t;
typedef int32_t glz_soff_t;
typedef uint32_t glz_size_t;
typedef int32_t glz_ssize_t;


// GLZ decode logic
int glz_decode(uint8_t k,
        glz_ssize_t (*read)(void *ctx, void *buf, glz_size_t size),
        void *read_ctx,
        glz_soff_t (*seek)(void *ctx, glz_off_t off),
        void *seek_ctx,
        glz_off_t off,
        glz_ssize_t (*write)(void *ctx, const void *buf, glz_size_t size),
        void *write_ctx,
        glz_size_t size) {
    // glz "stack"
    glz_off_t poff = 0;
    glz_size_t psize = 0;
    // buffer
    glz_ssize_t res;
    uint8_t buf[2];

    while (size > 0) {
        // decode rice code
        uint_fast16_t rice = 0;
        while (true) {
            res = seek(seek_ctx, off/8);
            if (res < 0) {
                return res;
            }
            res = read(read_ctx, buf, 1);
            if (res < 1) {
                if (res < 0) {
                    return res;
                }
                return GLZ_ERR_INVAL;
            }
            if (!(1 & (buf[0] >> (7-off%8)))) {
                off += 1;
                break;
            }
            rice += 1;
            off += 1;
        }
        for (glz_off_t i = 0; i < k; i++) {
            res = seek(seek_ctx, off/8);
            if (res < 0) {
                return res;
            }
            res = read(read_ctx, buf, 1);
            if (res < 1) {
                if (res < 0) {
                    return res;
                }
                return GLZ_ERR_INVAL;
            }
            rice = (rice << 1) | (1 & (buf[0] >> (7-off%8)));
            off += 1;
        }

        // map through table
        res = seek(seek_ctx, (9*rice)/8);
        if (res < 0) {
            return res;
        }
        res = read(read_ctx, buf, 2);
        if (res < 2) {
            if (res < 0) {
                return res;
            }
            return GLZ_ERR_INVAL;
        }
        rice = 0x1ff & (
            (buf[0] << 8) |
            (buf[1] << 0)) >> (7-(9*rice)%8);

        // indirect reference or literal?
        if (rice < 0x100) {
            ssize_t res = write(write_ctx, &(uint8_t){rice}, 1);
            if (res < 0) {
                return res;
            }
            size -= 1;
        } else {
            glz_size_t nsize = (rice & 0xff) + 2;
            glz_off_t noff = 0;
            while (true) {
                glz_off_t n = 0;
                for (glz_off_t i = 0; i < GLZ_M+1; i++) {
                    res = seek(seek_ctx, off/8);
                    if (res < 0) {
                        return res;
                    }
                    res = read(read_ctx, buf, 1);
                    if (res < 1) {
                        if (res < 0) {
                            return res;
                        }
                        return GLZ_ERR_INVAL;
                    }
                    n = (n << 1) | (1 & (buf[0] >> (7-off%8)));
                    off += 1;
                }

                noff = (noff << GLZ_M) + 1 + (n & ((1 << GLZ_M)-1));
                if (n < (1 << GLZ_M)) {
                    break;
                }
            }
            noff -= 1;

            // tail recurse?
            if (nsize >= size) {
                off = off + noff;
                size = size;
            } else {
                poff = off;
                psize = size - nsize;
                off = off + noff;
                size = nsize;
            }
        }

        if (size == 0) {
            off = poff;
            size = psize;
            poff = 0;
            psize = 0;
        }
    }

    return 0;
}


// helper functions that also decode limited
// GLZ metadata (size/k/table) from the blob
// [- 24 -|4|4|--  32  --][--  ...  --]
//     ^   ^ ^      ^           ^- compressed blob
//     |   | |      '- size of output in bytes
//     |   | '-------- k constant
//     |   '---------- 1 (glz format)
//     '-------------- offset from table in bits
glz_ssize_t glz_getsize(
        glz_ssize_t (*read)(void *ctx, void *buf, glz_size_t size),
        void *read_ctx,
        glz_soff_t (*seek)(void *ctx, glz_off_t off),
        void *seek_ctx) {
    glz_soff_t res = seek(seek_ctx, 4);
    if (res < 0) {
        return res;
    }

    uint8_t buf[4];
    res = read(read_ctx, buf, sizeof(buf));
    if (res < sizeof(buf)) {
        if (res < 0) {
            return res;
        }
        return GLZ_ERR_INVAL;
    }

    return ((uint32_t)buf[0] << 0) |
            ((uint32_t)buf[1] << 8) |
            ((uint32_t)buf[2] << 16) |
            ((uint32_t)buf[3] << 24);
}

glz_soff_t glz_getoff(
        glz_ssize_t (*read)(void *ctx, void *buf, glz_size_t size),
        void *read_ctx,
        glz_soff_t (*seek)(void *ctx, glz_off_t off),
        void *seek_ctx) {
    glz_soff_t res = seek(seek_ctx, 0);
    if (res < 0) {
        return res;
    }

    uint8_t buf[3];
    res = read(read_ctx, buf, sizeof(buf));
    if (res < sizeof(buf)) {
        if (res < 0) {
            return res;
        }
        return GLZ_ERR_INVAL;
    }

    return ((uint32_t)buf[4] << 0) |
            ((uint32_t)buf[5] << 8) |
            ((uint32_t)buf[6] << 16);
}

int glz_getk(
        glz_ssize_t (*read)(void *ctx, void *buf, glz_size_t size),
        void *read_ctx,
        glz_soff_t (*seek)(void *ctx, glz_off_t off),
        void *seek_ctx) {
    glz_soff_t res = seek(seek_ctx, 3);
    if (res < 0) {
        return res;
    }

    uint8_t buf[1];
    res = read(read_ctx, buf, sizeof(buf));
    if (res < sizeof(buf)) {
        if (res < 0) {
            return res;
        }
        return GLZ_ERR_INVAL;
    }

    return 0xf & buf[0];
}

struct glz_decode_all_seek_ctx {
    glz_soff_t (*seek)(void *ctx, glz_off_t off);
    void *ctx;
    glz_soff_t off;
};

static glz_soff_t glz_decode_all_read(void *p, glz_off_t off) {
    struct glz_decode_all_seek_ctx *ctx = p;
    // adjust offset for metadata
    return ctx->seek(ctx->ctx, off - ctx->off);
}

static glz_soff_t glz_decode_all_seek(void *p, glz_off_t off) {
    struct glz_decode_all_seek_ctx *ctx = p;
    // adjust offset for metadata
    return ctx->seek(ctx->ctx, off - ctx->off);
}

int glz_decode_all(
        glz_ssize_t (*read)(void *ctx, void *buf, glz_size_t size),
        void *read_ctx,
        glz_soff_t (*seek)(void *ctx, glz_off_t off),
        void *seek_ctx,
        glz_ssize_t (*write)(void *ctx, const void *buf, glz_size_t size),
        void *write_ctx,
        glz_size_t size) {
    glz_soff_t res = seek(seek_ctx, 0);
    if (res < 0) {
        return res;
    }

    uint8_t buf[8];
    res = read(read_ctx, buf, sizeof(buf));
    if (res < sizeof(buf)) {
        if (res < 0) {
            return res;
        }
        return GLZ_ERR_INVAL;
    }

    glz_soff_t off = ((uint32_t)buf[0] << 0) |
            ((uint32_t)buf[1] << 8) |
            ((uint32_t)buf[2] << 16);
    uint8_t k = 0xf & buf[3];

    glz_size_t nsize = ((uint32_t)buf[4] << 0) |
            ((uint32_t)buf[5] << 8) |
            ((uint32_t)buf[6] << 16) |
            ((uint32_t)buf[7] << 24);
    if (nsize < size) {
        size = nsize;
    }

    return glz_decode(k, read, read_ctx,
            glz_decode_all_seek,
            &(struct glz_decode_all_seek_ctx){seek, read_ctx, -8},
            off,
            write, write_ctx, size);
}

int glz_decode_slice(
        glz_ssize_t (*read)(void *ctx, void *buf, glz_size_t size),
        void *read_ctx,
        glz_soff_t (*seek)(void *ctx, glz_off_t off),
        void *seek_ctx,
        glz_off_t off,
        glz_ssize_t (*write)(void *ctx, const void *buf, glz_size_t size),
        void *write_ctx,
        glz_size_t size) {
    int k = glz_getk(read, read_ctx, seek, seek_ctx);
    if (k < 0) {
        return k;
    }

    return glz_decode(k, read, read_ctx,
            glz_decode_all_seek,
            &(struct glz_decode_all_seek_ctx){seek, read_ctx, -8},
            off,
            write, write_ctx, size);
}

// main isn't needed, just presents a CLI for testing/benchmarking
glz_ssize_t main_read(void *ctx, void *buf, glz_size_t size) {
    size_t res = fread(buf, 1, size, ctx);
    if (ferror(ctx)) {
        fprintf(stderr, "could not read?\n");
        return -errno;
    }
    return res;
}

glz_soff_t main_seek(void *ctx, glz_off_t off) {
    int err = fseek(ctx, off, SEEK_SET);
    if (err) {
        fprintf(stderr, "could not seek?\n");
        return -errno;
    }
    return ftell(ctx);
}

glz_ssize_t main_write(void *ctx, const void *buf, glz_size_t size) {
    size_t res = fwrite(buf, 1, size, ctx);
    if (ferror(ctx)) {
        fprintf(stderr, "could not write?\n");
        return -errno;
    }
    return res;
}

int main(int argc, char **argv) {
    if (argc != 2 && argc != 4) {
        fprintf(stderr, "usage: %s <file> [<off> <size>]\n", argv[0]);
        return 1;
    }

    bool slice = false;
    glz_off_t slice_off;
    glz_off_t slice_size;

    // requesting slice?
    if (argc == 4) {
        char *end;
        slice_off = strtol(argv[2], &end, 0);
        if (*end != '\0') {
            fprintf(stderr, "bad offset \"%s\"?\n", argv[2]);
            return 1;
        }

        slice_size = strtol(argv[3], &end, 0);
        if (*end != '\0') {
            fprintf(stderr, "bad size \"%s\"?\n", argv[3]);
            return 1;
        }

        slice = true;
    }

    // mmap file
    FILE *input = fopen(argv[1], "r");
    if (!input) {
        fprintf(stderr, "could not open file \"%s\"?\n", argv[1]);
        return 1;
    }

    // decode!
    if (slice) {
        int err = glz_decode_slice(
                main_read, input, main_seek, input, slice_off,
                main_write, stdout, slice_size);
        if (err) {
            fprintf(stderr, "decode failure %d :(\n", err);
            return 2;
        }
    } else {
        int err = glz_decode_all(
                main_read, input, main_seek, input,
                main_write, stdout, -1);
        if (err) {
            fprintf(stderr, "decode failure %d :(\n", err);
            return 2;
        }
    }

    return 0;
}
