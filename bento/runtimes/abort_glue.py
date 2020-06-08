from .. import runtimes

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

class AbortGlue(runtimes.Runtime):
    """
    Helper layer for handling __box_abort and friends.
    """
    __name = 'abort_glue'
    def box_box(self, box):
        self._abort_hook = box.addimport(
            '__box_abort', 'fn(err32) -> void',
            target=box.name, source=self.__name, weak=True,
            doc="May be called by a well-behaved code to terminate the box "
                "if execution can not continue. Notably used for asserts. "
                "Note that __box_abort may be skipped if the box is killed "
                "because of an illegal operation. Must not return.")

        super().box_box(box)

    def build_box_c(self, output, box):
        super().build_box_c(output, box)

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

        if box.emit_stdlib_hooks:
            output.includes.append('<stdio.h>')
            output.decls.append(BOX_STDLIB_HOOKS)

    def build_box_mk(self, output, box):
        super().build_box_mk(output, box)

        if box.emit_stdlib_hooks:
            output.decls.append('### __box_abort glue ###')
            output.decls.append('override LFLAGS += -Wl,--wrap,abort')


