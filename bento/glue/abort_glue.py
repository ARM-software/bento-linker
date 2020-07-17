from .. import glue

BOX_STDLIB_HOOKS = """
__attribute__((used, noreturn))
void __wrap_abort(void) {
    __box_abort(-1);
}

#ifdef __GNUC__
__attribute__((noreturn))
void __assert_func(const char *file, int line,
        const char *func, const char *expr) {
    printf("%%s:%%d: assertion \\"%%s\\" failed\\n", file, line, expr);
    __box_abort(-1);
}

__attribute__((noreturn))
void _exit(int returncode) {
    __box_abort(-returncode);
}
#endif
"""

BOX_RUST_HOOKS = '''
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
        self._abort_hook = box.addimport(
            '__box_abort', 'fn(err32) -> void',
            target=box.name, source=self.__name, weak=True,
            doc="May be called by well-behaved code to terminate the box "
                "if execution can not continue. Notably used for asserts. "
                "Note that __box_abort may be skipped if the box is killed "
                "because of an illegal operation. Must not return.")

    def build_c(self, output, box):
        super().build_c(output, box)

        output.decls.append('//// __box_abort glue ////')
        if not self._abort_hook.link:
            # defaults to just halting
            out = output.decls.append()
            out.printf('__attribute__((noreturn))')
            out.printf('void __box_abort(int err) {')
            with out.indent():
                out.printf('// if there\'s no other course of action, we spin')
                out.printf('while (1) {}')
            out.printf('}')
        elif self._abort_hook.link.export.alias != '__box_abort':
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
            output.decls.append(BOX_STDLIB_HOOKS)

    def build_mk(self, output, box):
        super().build_mk(output, box)

        if ('c' in box.outputs and
                not box.outputs[box.outputs.index('c')].no_stdlib_hooks):
            out = output.decls.append()
            out.printf('### __box_abort glue ###')
            out.printf('override LDFLAGS += -Wl,--wrap,abort')

    def build_rs(self, output, box):
        super().build_rs(output, box)
        # TODO doc
        output.uses.append('core::panic')
        output.decls.append(BOX_RUST_HOOKS)
