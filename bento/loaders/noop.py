from .. import loaders
import os

@loaders.loader
class NoOpLoader(loaders.Loader):
    """
    A loader that does nothing, allowing execution in
    the specified flash and RAM.
    """
    __argname__ = "noop"
    __arghelp__ = __doc__
    def __init__(self):
        super().__init__()

    def box_parent(self, parent, box):
        super().box_parent(parent, box)
        self._load_plug = parent.addexport(
            '__box_%s_load' % box.name, 'fn() -> err',
            scope=parent.name, source=self.__argname__, weak=True)

    def build_mk(self, output, box):
        # target rule
        out = output.rules.append(doc='target rule')
        out.printf('$(TARGET): $(OBJ) $(ARCHIVES) $(BOXES) $(LDSCRIPT)')
        with out.indent():
            out.printf('$(CC) $(OBJ) $(BOXES) $(LDFLAGS) -o $@')

        # create boxing rule, to be invoked if embedding an elf is needed
        data_init = None
        if any(section.name == 'data'
                for memory in box.memoryslices
                for section in memory.sections):
            data_init = box.consume('rp', 0)

        loadmemories = []
        for memory in box.memoryslices:
            if 'p' in memory.mode:
                loadmemories.append((memory.name, memory,
                    [section.name for section in memory.sections]))
        for child in box.boxes:
            for memory in child.memories:
                if 'p' in memory.mode:
                    name = 'box.%s.%s' % (child.name, memory.name)
                    loadmemories.append((name, memory, [name]))

        out = output.rules.append(
            doc="a .box is a .elf containing a single section for "
                "each loadable memory region")
        out.printf('%%.box: %%.elf %(memory_boxes)s',
            memory_boxes=' '.join(
                '%.box.'+name for name, _, _ in loadmemories))
        with out.indent():
            out.writef('$(strip $(OBJCOPY) $< $@')
            with out.indent():
                # objcopy won't let us create an empty elf, but we can
                # fake it by treating the input as binary and striping
                # all implicit sections. Needed to get rid of program
                # segments which create warnings later.
                out.writef(' \\\n-I binary')
                out.writef(' \\\n-O elf32-littlearm')
                out.writef(' \\\n-B arm')
                out.writef(' \\\n--strip-all')
                out.writef(' \\\n--remove-section=*')
                for i, (name, memory, _) in enumerate(loadmemories):
                    with out.pushattrs(
                            memory=name,
                            addr=memory.addr,
                            n=2+i):
                        out.writef(' \\\n--add-section '
                            '.box.%(box)s.%(memory)s=$(word %(n)d,$^)')
                        out.writef(' \\\n--change-section-address '
                            '.box.%(box)s.%(memory)s=%(addr)#.8x')
                        out.writef(' \\\n--set-section-flags '
                            '.box.%(box)s.%(memory)s='
                            'contents,alloc,load,readonly,data')
                out.printf(')')

        for name, _, sections in loadmemories:
            out = output.rules.append()
            out.printf('%%.box.%(memory)s: %%.elf', memory=name)
            with out.indent():
                out.writef('$(strip $(OBJCOPY) $< $@')
                with out.indent():
                    for section in sections:
                        out.writef(' \\\n--only-section .%(section)s',
                            section=section)
                        # workaround to get the data_init section in the
                        # right place
                        if section == 'text' and data_init is not None:
                            out.writef(' \\\n--only-section .data')
                    out.printf(' \\\n-O binary)\n')

        super().build_mk(output, box)

    def build_parent_c(self, output, parent, box):
        super().build_parent_c(output, parent, box)
        if not self._load_plug.links:
            # if someone else provides load we can just skip this
            return

        output.decls.append('//// %(box)s loading ////')
        out = output.decls.append()
        out.printf("static int __box_%(box)s_load(void) {")
        with out.indent():
            out.printf("// default loader does nothing")
            out.printf("return 0;")
        out.printf("}")
