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


class HeapGlue(glue.Glue):
    """
    Helper layer for handling heap related functions.
    """
    __name = 'heap_glue'

    def build_c(self, output, box):
        super().build_c(output, box)
        if not output.no_stdlib_hooks:
            output.decls.append(GCC_HOOKS)

