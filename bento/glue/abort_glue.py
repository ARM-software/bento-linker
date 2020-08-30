from .. import glue

C_HOOKS = """
%(visibility)s
__attribute__((noreturn))
void __wrap_abort(void) {
    __box_abort(-1);
}

%(visibility)s
void __wrap_exit(int code) {
    __box_abort(code > 0 ? -code : code);
}
"""

GCC_HOOKS = """
#if defined(__GNUC__)
__attribute__((noreturn))
void __assert_func(const char *file, int line,
        const char *func, const char *expr) {
    printf("%%s:%%d: assertion \\"%%s\\" failed\\n", file, line, expr);
    __box_abort(-1);
}

__attribute__((noreturn))
void _exit(int code) {
    __box_abort(code > 0 ? -code : code);
}
#endif
"""

WASM_HOOKS = """
__attribute__((noreturn))
void __assert_fail(const char *m,
        const char *file, int32_t line, const char *func) {
    printf("assert failed: %%s\\n", m);
    __box_abort(-1);
}
"""

RUST_HOOKS = '''
/// abort implementation
pub fn abort(err: Error) -> ! {
    extern "C" {
        pub fn __box_abort(err: i32) -> !;
    }

    let err = -err.get_i32();
    unsafe {
        __box_abort(err)
    }
}

/// panic handler which redirects to abort, passes Error types
/// through as error codes
#[panic_handler]
fn panic_handler(_info: &panic::PanicInfo) -> ! {
    extern "C" {
        pub fn __box_abort(err: i32) -> !;
    }

    // don't use anything from the PanicInfo, unfortunately
    // this would drag in a bunch of debug strings
    abort(Error::General)
}
'''

class AbortGlue(glue.Glue):
    """
    Helper layer for handling __box_abort and friends.
    """
    __name = 'abort_glue'
    def box(self, box):
        super().box(box)
        self.__abort_hook = box.addimport(
            '__box_abort', 'fn(err err) -> noreturn',
            scope=box.name, source=self.__name, weak=True,
            doc="May be called by well-behaved code to terminate the box "
                "if execution can not continue. Notably used for asserts. "
                "Note that __box_abort may be skipped if the box is killed "
                "because of an illegal operation. Must not return.")

    def __build_common_prologue(self, output, box):
        output.decls.append('%(fn)s;',
            fn=output.repr_fn(self.__abort_hook),
            doc=self.__abort_hook.doc)

    def build_h_prologue(self, output, box):
        super().build_h_prologue(output, box)
        self.__build_common_prologue(output, box)

    def build_c_prologue(self, output, box):
        super().build_c_prologue(output, box)
        self.__build_common_prologue(output, box)

    def build_wasm_h_prologue(self, output, box):
        super().build_h_prologue(output, box)
        self.__build_common_prologue(output, box)

    def build_wasm_c_prologue(self, output, box):
        super().build_c_prologue(output, box)
        self.__build_common_prologue(output, box)

    def __build_common_c(self, output, box):
        output.decls.append('//// __box_abort glue ////')
        if not self.__abort_hook.link:
            # defaults to just halting
            out = output.decls.append()
            out.printf('__attribute__((noreturn))')
            out.printf('void __box_abort(int err) {')
            with out.indent():
                out.printf('// if there\'s no other course of action, we spin')
                out.printf('while (1) {}')
            out.printf('}')
        elif self.__abort_hook.link.export.alias != '__box_abort':
            # jump to correct implementation
            out = output.decls.append()
            out.printf('__attribute__((noreturn))')
            out.printf('void __box_abort(int err) {')
            with out.indent():
                out.printf('%(alias)s(err);',
                    alias=self._write_hook.link.export.alias)
            out.printf('}')

        if not output.no_stdlib_hooks:
            output.includes.append('<stdio.h>')
            output.decls.append(C_HOOKS)

    def build_c(self, output, box):
        super().build_c(output, box)

        with output.pushattrs(
                visibility='__attribute__((used))'):
            self.__build_common_c(output, box)

            if not output.no_stdlib_hooks:
                output.decls.append(GCC_HOOKS)

    def build_wasm_c(self, output, box):
        super().build_wasm_c(output, box)

        with output.pushattrs(
                visibility='__attribute__((visibility("hidden")))'):
            self.__build_common_c(output, box)

            if not output.no_stdlib_hooks:
                output.decls.append(WASM_HOOKS)

    def build_mk(self, output, box):
        super().build_mk(output, box)

        out = output.decls.append()
        out.printf('### __box_abort glue ###')
        if ('c' in box.outputs and
                not box.outputs[box.outputs.index('c')].no_stdlib_hooks):
            out.printf('override LDFLAGS += -Wl,--wrap,abort')
            out.printf('override LDFLAGS += -Wl,--wrap,exit')
        if (not output.no_wasm and
                'wasm_c' in box.outputs and
                not box.outputs[box.outputs.index('wasm_c')].no_stdlib_hooks):
            out.printf('override WASMLDFLAGS += -Wl,--wrap,abort')
            out.printf('override WASMLDFLAGS += -Wl,--wrap,exit')

    def __build_common_rust_lib(self, output, box):
        output.uses.append('core::panic')
        output.decls.append(RUST_HOOKS)

    def build_rust_lib(self, output, box):
        super().build_rust_lib(output, box)
        self.__build_common_rust_lib(output, box)

    def build_wasm_rust_lib(self, output, box):
        super().build_wasm_rust_lib(output, box)
        self.__build_common_rust_lib(output, box)
