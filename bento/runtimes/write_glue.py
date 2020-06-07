from .. import runtimes

BOX_STDLIB_HOOKS = """
#ifdef __GNUC__
int _write(int handle, char *buffer, int size) {
    return %(write_hook)s(handle, (uint8_t*)buffer, size);
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

        self._child_write_hooks = []
        for child in box.boxes:
            self._child_write_hooks.append(box.addimport(
                '__box_%s_write' % child.name, 'fn(i32, u8*, usize) -> errsize',
                target=box.name, source=self.__name, weak=True,
                doc="Override __box_write for a specific box."))

        super().box_box(box)

    def build_box_c(self, output, box):
        super().build_box_c(output, box)
        output.pushattrs(
            write_hook=self._write_hook.link.export.alias
                if self._write_hook.link else '__box_write')

        output.decls.append('//// __box_write glue ////')
        if not self._write_hook.link:
            out = output.decls.append()
            out.printf('ssize_t __box_write(int32_t fd, '
                'void *buffer, size_t size) {')
            with out.indent():
                out.printf('return size;')
            out.printf('}')

        if any(not hook.link for hook in self._child_write_hooks):
            out = output.decls.append()
            for hook, child in zip(self._child_write_hooks, box.boxes):
                if not hook.link:
                    out.printf('#define __box_%(box)s_write %(write_hook)s',
                        box=child.name)

        output.decls.append(BOX_STDLIB_HOOKS)

