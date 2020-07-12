from .. import loaders
from ..box import Section


BOX_GLZ_DECODE = """
// GLZ constants
#ifndef GLZ_M
#define GLZ_M 4
#endif
typedef uint32_t glz_size_t;
typedef uint32_t glz_off_t;

int __box_glz_decode(uint8_t k,
        const uint8_t *blob, glz_size_t blob_size, glz_off_t off,
        uint8_t *output, glz_size_t size) {
    // glz "stack"
    glz_off_t poff = 0;
    glz_size_t psize = 0;

    while (size > 0) {
        // decode rice code
        uint_fast16_t rice = 0;
        while (true) {
            if (off/8 >= blob_size) {
                return -EINVAL;
            }
            if (!(1 & (blob[off/8] >> (7-off%%8)))) {
                off += 1;
                break;
            }
            rice += 1;
            off += 1;
        }
        for (glz_off_t i = 0; i < k; i++) {
            if (off/8 >= blob_size) {
                return -EINVAL;
            }
            rice = (rice << 1) | (1 & (blob[off/8] >> (7-off%%8)));
            off += 1;
        }

        // map through table
        if ((9*rice)/8+1 >= blob_size) {
            return -EINVAL;
        }
        rice = 0x1ff & (
            (blob[(9*rice)/8+0] << 8) |
            (blob[(9*rice)/8+1] << 0)) >> (7-(9*rice)%%8);

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
                    if (off/8 >= blob_size) {
                        return -EINVAL;
                    }
                    n = (n << 1) | (1 & (blob[off/8] >> (7-off%%8)));
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
"""

BOX_DECODE = """
int __box_%(box)s_load(void) {
    extern const uint32_t __box_%(box)s_blob_start[];
    extern const uint8_t __box_%(box)s_blob_end;
    extern uint32_t __box_%(box)s_%(memory)s_start;
    extern uint32_t __box_%(box)s_%(memory)s_end;

    // load metadata
    uint32_t x = __box_%(box)s_blob_start[0];
    uint8_t k = 0xf & (x >> 24);
    uint32_t off = 0x00ffffff & x;
    uint32_t size = __box_%(box)s_blob_start[1];
    if (size > (uint8_t*)&__box_%(box)s_%(memory)s_end
            - (uint8_t*)&__box_%(box)s_%(memory)s_start) {
        // can't allow overwrites now can we
        return -ENOEXEC;
    }

    // decompress
    return __box_glz_decode(k,
            (const uint8_t*)&__box_%(box)s_blob_start[2],
            &__box_%(box)s_blob_end
                - (const uint8_t*)&__box_%(box)s_blob_start[2],
            off,
            (uint8_t*)&__box_%(box)s_%(memory)s_start, 
            size);
}
"""

# a little bit more complex when multiple regions are involved
BOX_DECODE_MULTI = """
int __box_%(box)s_load(void) {
    extern const uint32_t __box_%(box)s_blob_start[];
    extern const uint8_t __box_%(box)s_blob_end;

    // load metadata
    uint32_t x = __box_%(box)s_blob_start[0];
    uint8_t k = 0xf & (x >> 24);
    uint32_t count = 0x00ffffff & x;
    if (count != %(n)d) {
        return -ENOEXEC;
    }

    for (uint32_t i = 0; i < %(n)d; i++) {
        uint32_t off = __box_%(box)s_blob_start[1+2*i+0];
        uint32_t size = __box_%(box)s_blob_start[1+2*i+1];
        if (size > __box_%(box)s_loadregions[i][1]
                - __box_%(box)s_loadregions[i][0]) {
            // can't allow overwrites now can we
            return -ENOEXEC;
        }

        // decompress region
        int err = __box_glz_decode(k,
                (const uint8_t*)&__box_%(box)s_blob_start[1+2*%(n)d],
                &__box_%(box)s_blob_end
                    - (const uint8_t*)&__box_%(box)s_blob_start[1+2*%(n)d],
                off,
                __box_%(box)s_loadregions[i][0],
                size);
        if (err) {
            return err;
        }
    }

    return 0;
}
"""

@loaders.loader
class GLZLoader(loaders.Loader):
    """
    A loader that implements GLZ decompression, a compression
    algorithm designed for microcontrollers with very
    lightweight decompression.
    """
    __argname__ = "glz"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser, **kwargs):
        parser.add_nestedparser('--blob', Section)
        parser.add_argument('--glz',
            help='Override the GLZ path for the makefile.')
        parser.add_argument('--glz_flags', type=list,
            help='Add custom GLZ flags.')

    def __init__(self, blob=None, glz=None, glz_flags=None):
        super().__init__()
        self._blob = Section('blob', **blob.__dict__)
        self._glz = glz or 'glz'
        self._glz_flags = glz_flags or []

    def constraints(self, constraints):
        if 'c' in constraints['mode']:
            # workaround to let compressed requests through normally
            constraints['mode'].discard('c')
        else:
            constraints['mode'].discard('p')
            constraints['mode'].add('w')

    def box(self, box):
        super().box(box)
        # special compressed blob section
        self._blob.alloc(box, 'rpc')
        # we also take care data implicitly
        box.addexport('__box_data_init', 'fn() -> void',
            target=box.name, source=self.__argname__, weak=True)

    def build_ld(self, output, box):
        if output.emit_sections:
            out = output.sections.append(
                section='.blob',
                memory=self._blob.memory.name)
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__blob_start = .;')
            out.printf('%(section)s . : {')
            with out.pushindent():
                out.printf('KEEP(*(.blob))')
            out.printf('} > %(MEMORY)s')
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__blob_end = .;')

        super().build_ld(output, box)

    def build_parent_ld(self, output, sys, box):
        super().build_parent_ld(output, sys, box)

        if output.emit_sections:
            out = output.sections.append(
            box_memory=self._blob.memory.name,
                section='.box.%(box)s.%(box_memory)s',
                memory='box_%(box)s_%(box_memory)s')
            out.printf('__box_%(box)s_blob_start = __%(memory)s_start;')
            out.printf('__box_%(box)s_blob_end = __%(memory)s_end;')

    def build_mk_prologue(self, output, box):
        super().build_mk_prologue(output, box)
        out = output.decls.append()
        out.printf('%(name)-16s ?= %(path)s',
            name='GLZ',
            # TODO relative path?
            path=self._glz)

        out = output.decls.append()
        out.printf('override GLZFLAGS += -q')
        out.printf('override GLZFLAGS += -n')
        if self._glz_flags:
            out.printf('# user provided')
        for flag in self._glz_flags:
            out.printf('override GLZFLAGS += %s' % flag)

    def build_mk(self, output, box):
        super().build_mk(output, box)

        # target rule
        out = output.rules.append(doc='target rule')
        out.printf('$(TARGET): $(OBJ) $(BOXES) $(LDSCRIPT)')
        with out.indent():
            out.printf('$(CC) $(OBJ) $(BOXES) $(LFLAGS) -o $@')

        # create boxing rule, to be invoked if embedding an elf is needed
        loadmemories = []
        for memory in box.memoryslices:
            if 'w' in memory.mode:
                loadmemories.append((memory.name, memory,
                    [section.name for section in memory.sections]))
        for child in box.boxes:
            if 'w' in memory.mode:
                for memory in child.memories:
                    name = 'box.%s.%s' % (child.name, memory.name)
                    loadmemories.append((name, memory, [name]))

        out = output.rules.append(
            doc="a .box is a .elf containing a single section for "
                "each loadable memory region")
        out.printf('%%.box: %%.elf %%.box.glz')
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
                with out.pushattrs(
                        memory=self._blob.memory.name,
                        addr=self._blob.memory.addr,
                        section='blob'):
                    out.writef(' \\\n--add-section '
                        '.box.%(box)s.%(memory)s=$(word 2,$^)')
                    out.writef(' \\\n--change-section-address '
                        '.box.%(box)s.%(memory)s=%(addr)#.8x')
                    out.writef(' \\\n--set-section-flags '
                        '.box.%(box)s.%(memory)s='
                        'contents,alloc,load,readonly,data')
                out.printf(')')

        out.printf('%%.box.glz: %(memory_boxes)s',
            memory_boxes=' '.join(
                '%.box.'+name for name, _, _ in loadmemories))
        with out.indent():
            if len(loadmemories) == 1:
                out.printf('$(GLZ) encode $(GLZFLAGS) $^ -o $@')
            else:
                out.printf('$(GLZ) encode -I $(GLZFLAGS) $^ -o $@')

        for name, _, sections in loadmemories:
            out = output.rules.append()
            out.printf('%%.box.%(memory)s: %%.elf', memory=name)
            with out.indent():
                out.writef('$(strip $(OBJCOPY) $< $@')
                with out.indent():
                    for section in sections:
                        out.writef(' \\\n--only-section .%(section)s',
                            section=section)
                    out.printf(' \\\n-O binary)\n')

    def box_parent(self, parent, box):
        super().box_parent(parent, box)
        self._load_plug = parent.addexport(
            '__box_%s_load' % box.name, 'fn() -> err',
            target=parent.name, source=self.__argname__, weak=True)

    def build_parent_c_prologue(self, output, parent):
        super().build_parent_c_prologue(output, parent)
        output.decls.append(BOX_GLZ_DECODE)

    def build_parent_c(self, output, parent, box):
        super().build_parent_c(output, parent, box)
        if not self._load_plug.links:
            # if someone else provides load we can just skip this
            return

        loadmemories = []
        for memory in box.memoryslices:
            if 'w' in memory.mode:
                loadmemories.append((memory.name, memory,
                    [section.name for section in memory.sections]))
        for child in box.boxes:
            if 'w' in memory.mode:
                for memory in child.memories:
                    name = 'box.%s.%s' % (child.name, memory.name)
                    loadmemories.append((name, memory, [name]))

        output.decls.append('//// %(box)s loading ////')

        if len(loadmemories) == 1:
            # if we only have one memory region (common), we can use
            # slightly less metadata
            output.decls.append(BOX_DECODE, memory=loadmemories[0][0])
        else:
            # otherwise, dynamically generate a loader that can handle
            # all the memory regions
            out = output.decls.append()
            for memory, _, _ in loadmemories:
                with out.pushattrs(memory=memory):
                    out.printf('extern uint32_t '
                        '__box_%(box)s_%(memory)s_start;')
                    out.printf('extern uint32_t '
                        '__box_%(box)s_%(memory)s_end;')
            out.printf('uint8_t *const __box_%(box)s_loadregions[][2] = {')
            with out.indent():
                for memory, _, _ in loadmemories:
                    with out.pushattrs(memory=memory):
                        out.printf('{'
                            '(uint32_t*)&__box_%(box)s_%(memory)s_start, '
                            '(uint32_t*)&__box_%(box)s_%(memory)s_end}')
            out.printf('};')

            out = output.decls.append(BOX_DECODE_MULTI, n=len(loadmemories))

