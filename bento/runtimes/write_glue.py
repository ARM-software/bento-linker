from .. import runtimes

BOX_STDLIB_HOOKS = """
#ifdef __GNUC__
int _write(int handle, char *buffer, int size) {
    return __box_write(handle, (uint8_t*)buffer, size);
}
#endif
"""

class WriteGlue(runtimes.Runtime):
    """
    Helper layer for handling __box_write and friends.
    """
    __name = 'write_glue'
    def box_box(self, box):
        self._write_hook = box.addimport(
            '__box_write', 'fn(i32, u8*, usize) -> errsize',
            target=box.name, source=self.__name, weak=True,
            doc="Provides a minimal implementation of stdout to the box. "
                "The exact behavior depends on the superbox's implementation "
                "of __box_write. If none is provided, __box_write links but "
                "does nothing.")

        super().box_box(box)

    def build_box_c(self, output, box):
        super().build_box_c(output, box)

        output.decls.append('//// __box_write glue ////')
        if not self._write_hook.link:
            # defaults to noop
            out = output.decls.append()
            out.printf('ssize_t __box_write(int32_t fd, '
                'void *buffer, size_t size) {')
            with out.indent():
                out.printf('return size;')
            out.printf('}')
        elif self._write_hook.link.export.alias != '__box_write':
            # jump to correct implementation
            out = output.decls.append()
            out.printf('ssize_t __box_write(int32_t fd, '
                'void *buffer, size_t size) {')
            with out.indent():
                out.printf('return %(alias)s(fd, buffer, size);',
                    alias=self._write_hook.link.export.alias)
            out.printf('}')

        output.decls.append(BOX_STDLIB_HOOKS)

