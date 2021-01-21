#
# Heap/memory allocation glue
# 
# Copyright (c) 2020, Arm Limited. All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause
#

from .. import glue

GCC_HOOKS = """
#if defined(__GNUC__)
// state of brk
static uint8_t *__heap_brk = NULL;
// assigned by linker
extern uint8_t __heap_start;
extern uint8_t __heap_end;

// GCC's _sbrk uses sp for bounds checking, this
// does not work if our stack is located before the heap
void *_sbrk(ptrdiff_t diff) {
    if (!__heap_brk) {
        __heap_brk = &__heap_start;
    }

    uint8_t *pbrk = __heap_brk;
    if (pbrk + diff > &__heap_end) {
        return (void*)-1;
    }

    __heap_brk = pbrk+diff;
    return pbrk;
}
#endif
"""


# quick heap implementation when unavailable in stdlib
# this is needed for wasm, not because there is no heap, but
# because the heap forces >1 pages (64 KiB each).
#
# note this does not free
#
# TODO replace this
REPLACE_ME_HEAP = """
ssize_t *__heap_start = NULL;
ssize_t *__heap_end;

void *__wrap_malloc(size_t size) {
    if (!__heap_start) {
        __heap_end = (ssize_t*)(__builtin_wasm_memory_size(0)*64*1024);
        __heap_start = __heap_end - %(heap_size)d/4;

        __heap_start[0] = %(heap_size)d/4 - 2;
        __heap_end[-1]  = %(heap_size)d/4 - 2;
    }

    size = (size+3) / 4;

    ssize_t *ptr = __heap_start;
    while (ptr < __heap_end) {
        // make sure heap isn't corrupted
        ssize_t psize = ptr[0];
        if (ptr[0] != ptr[(psize & 0x7fffffff)+2-1]) {
            __box_abort(-EFAULT);
        }

        // fits?
        if (psize >= (ssize_t)size) {
            // should split?
            if (psize >= size+2) {
                ptr[size+2]    = psize - (size+2);
                ptr[psize+2-1] = psize - (size+2);
                ptr[0]         = size;
                ptr[size+2-1]  = size;
                psize = size;
            }

            // mark as used
            ptr[0]        = psize | 0x80000000;
            ptr[size+2-1] = psize | 0x80000000;

            return ptr+1;
        }

        ptr += (psize & 0x7fffffff) + 2;
    }

    return NULL;
}

void __wrap_free(void *pptr) {
    if (!pptr) {
        return;
    }

    ssize_t *ptr = (ssize_t*)pptr - 1;
    ssize_t psize = ptr[0];

    // make sure heap isn't corrupted
    if (ptr[0] != ptr[(psize & 0x7fffffff)+2-1]) {
        __box_abort(-EFAULT);
    }

    psize = psize & 0x7fffffff;

    // coalesce blocks?
    while (true) {
        if (&ptr[-1] > __heap_start && ptr[-1] >= 0) {
            psize += ptr[-1] + 2;
            ptr -= ptr[-1] + 2;
        } else if (&ptr[psize+2] < __heap_end && ptr[psize+2] >= 0) {
            psize += ptr[psize+2] + 2;
        } else {
            break;
        }
    }

    // mark as free
    ptr[0]         = psize;
    ptr[psize+2-1] = psize;
}

void *__wrap_calloc(size_t size) {
    uint8_t *ptr = __wrap_malloc(size);
    memset(ptr, 0, size);
    return ptr;
}

void *__wrap_realloc(void *pptr, size_t size) {
    ssize_t psize = pptr ? ((ssize_t*)pptr)[-1] : 0;

    void *nptr = __wrap_malloc(size);
    if (nptr) {
        // yes this copies extra, we don't really care
        memmove(nptr, pptr, psize);

        __wrap_free(pptr);
    }

    return nptr;
}
"""


class HeapGlue(glue.Glue):
    """
    Helper layer for handling heap related functions.
    """
    __name = 'heap_glue'

    def build_c(self, output, box):
        super().build_c(output, box)
        if not output.no_stdlib_hooks:
            output.decls.append(GCC_HOOKS)

    def build_wasm_c(self, output, box):
        super().build_wasm_c(output, box)
        if not output.no_stdlib_hooks:
            output.decls.append(REPLACE_ME_HEAP,
                heap_size=box.heap.size)

    def build_mk(self, output, box):
        super().build_mk(output, box)
        if (not output.no_wasm and
                'wasm_c' in box.outputs and
                not box.outputs[box.outputs.index('wasm_c')].no_stdlib_hooks):
            out = output.decls.append()
            out.printf('### replace-me-heap glue ###')
            out.printf('override WASMLDFLAGS += -Wl,--wrap,malloc')
            out.printf('override WASMLDFLAGS += -Wl,--wrap,free')
            out.printf('override WASMLDFLAGS += -Wl,--wrap,calloc')
            out.printf('override WASMLDFLAGS += -Wl,--wrap,realloc')



