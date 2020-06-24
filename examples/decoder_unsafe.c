/*
 * Bare minimum implementation of a GLZ decoder, operates in
 * constant RAM and linear time.
 *
 * Does not provide bounds checking! So should not be used
 * unless you reaaaaally need the code size.
 */
#include <sys/types.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdlib.h>

#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
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
        const uint8_t *blob, glz_size_t blob_size, glz_off_t off,
        uint8_t *output, glz_size_t size) {
    // glz "stack"
    glz_off_t poff = 0;
    glz_size_t psize = 0;

    while (size > 0) {
        // decode rice code
        uint_fast16_t rice = 0;
        while (true) {
            if (!(1 & (blob[off/8] >> (7-off%8)))) {
                off += 1;
                break;
            }
            rice += 1;
            off += 1;
        }
        for (glz_off_t i = 0; i < k; i++) {
            rice = (rice << 1) | (1 & (blob[off/8] >> (7-off%8)));
            off += 1;
        }

        // map through table
        rice = 0x1ff & (
            (blob[(9*rice)/8+0] << 8) |
            (blob[(9*rice)/8+1] << 0)) >> (7-(9*rice)%8);

        // indirect reference or literal?
        if (rice < 0x100) {
            *output++ = rice;
            size -= 1;
        } else {
            glz_size_t nsize = (rice & 0xff) + 2;
            glz_off_t noff = 0;
            while (true) {
                glz_off_t n = 0;
                for (glz_off_t i = 0; i < GLZ_M+1; i++) {
                    n = (n << 1) | (1 & (blob[off/8] >> (7-off%8)));
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
glz_ssize_t glz_getsize(const uint8_t *blob, glz_size_t blob_size) {
    if (blob_size < 8) {
        return GLZ_ERR_INVAL;
    }

    return ((uint32_t)blob[4] << 0) |
            ((uint32_t)blob[5] << 8) |
            ((uint32_t)blob[6] << 16) |
            ((uint32_t)blob[7] << 24);
}

glz_soff_t glz_getoff(const uint8_t *blob, glz_size_t blob_size) {
    if (blob_size < 8) {
        return GLZ_ERR_INVAL;
    }

    return ((uint32_t)blob[0] << 0) |
            ((uint32_t)blob[1] << 8) |
            ((uint32_t)blob[2] << 16);
}

int glz_getk(const uint8_t *blob, glz_size_t blob_size) {
    if (blob_size < 8) {
        return GLZ_ERR_INVAL;
    }

    return 0xf & blob[3];
}

int glz_decode_all(const uint8_t *blob, glz_size_t blob_size,
        uint8_t *output, glz_size_t size) {
    if (blob_size < 8) {
        return GLZ_ERR_INVAL;
    }

    glz_off_t off = glz_getoff(blob, blob_size);
    uint8_t k = glz_getk(blob, blob_size);

    glz_size_t nsize = glz_getsize(blob, blob_size);
    if (nsize < size) {
        size = nsize;
    }

    return glz_decode(k, blob+8, blob_size-8, off, output, size);
}

int glz_decode_slice(const uint8_t *blob, glz_size_t blob_size, glz_off_t off,
        uint8_t *output, glz_size_t size) {
    if (blob_size < 8) {
        return GLZ_ERR_INVAL;
    }

    uint8_t k = glz_getk(blob, blob_size);
    return glz_decode(k, blob+8, blob_size-8, off, output, size);
}


// main isn't needed, just presents a CLI for testing/benchmarking
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
    int fd = open(argv[1], O_RDONLY, 0);
    if (fd < 0) {
        fprintf(stderr, "could not open file \"%s\"?\n", argv[1]);
        return 1;
    }

    struct stat fdstat;
    int err = fstat(fd, &fdstat);
    if (err) {
        fprintf(stderr, "file stat failed \"%s\"?\n", argv[1]);
        return 1;
    }
    size_t blob_size = fdstat.st_size;

    const uint8_t *blob = mmap(NULL, blob_size, PROT_READ, MAP_PRIVATE, fd, 0);
    if (blob == MAP_FAILED) {
        fprintf(stderr, "could not mmap file \"%s\"?\n", argv[1]);
        return 1;
    }

    // create output buffer
    glz_ssize_t size;
    if (slice) {
        size = slice_size;
    } else {
        size = glz_getsize(blob, blob_size);
        if (size < 0) {
            fprintf(stderr, "decode failure %d :(\n", size);
            return 2;
        }
    }

    uint8_t *output = malloc(size);
    if (!output) {
        fprintf(stderr, "could not allocated output (%d bytes)\n", size);
        return 3;
    }

    // decode!
    if (slice) {
        err = glz_decode_slice(blob, blob_size, slice_off, output, size);
        if (err) {
            fprintf(stderr, "decode failure %d :(\n", err);
            return 2;
        }
    } else {
        err = glz_decode_all(blob, blob_size, output, size);
        if (err) {
            fprintf(stderr, "decode failure %d :(\n", err);
            return 2;
        }
    }

    // dump
    ssize_t res = write(1, output, size);
    if (res < 0) {
        fprintf(stderr, "could not write?\n");
        return 3;
    }

    return 0;
}
