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
uint8_t *__heap_ptr;
uint8_t *__heap_end = 0;

void *__wrap_malloc(size_t size) {
    if (__heap_end == 0) {
        __heap_end = (uint8_t*)(__builtin_wasm_memory_size(0)*64*1024);
        __heap_ptr = __heap_end - %(heap_size)d;
    }

    size = ((size+3)/4)*4;
    if (__heap_ptr + size > __heap_end) {
        printf("replace_me_malloc: out of memory\\n");
        return NULL;
    }

    uint8_t *pptr = __heap_ptr;
    __heap_ptr += size;
    return pptr;
}

void __wrap_free(void *ptr) {
    printf("replace_me_malloc: warning, "
        "free called but does nothing\\n");
}

void *__wrap_calloc(size_t size) {
    uint8_t *ptr = __wrap_malloc(size);
    memset(ptr, 0, size);
    return ptr;
}

void *__wrap_realloc(void *ptr, size_t size) {
    printf("replace_me_malloc: warning, "
        "realloc called and is probably a bad idea\\n");
    void *nptr = __wrap_malloc(size);
    if (nptr) {
        // yes this copies extra, we don't really care
        memmove(nptr, ptr, size);
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



