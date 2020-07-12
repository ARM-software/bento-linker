from .. import loaders
from ..box import Region


# TODO make these actually common?
BOX_COMMON = """
__attribute__((unused))
static inline uint32_t __box_bd_max(uint32_t a, uint32_t b) {
    return (a > b) ? a : b;
}

__attribute__((unused))
static inline uint32_t __box_bd_min(uint32_t a, uint32_t b) {
    return (a < b) ? a : b;
}

__attribute__((unused))
static inline uint32_t __box_bd_aligndown(uint32_t a, uint32_t alignment) {
    return a - (a %% alignment);
}

__attribute__((unused))
static inline uint32_t __box_bd_alignup(uint32_t a, uint32_t alignment) {
    return __box_bd_aligndown(a + alignment-1, alignment);
}
"""

BOX_GLZ_DECODE = """
// GLZ constants
#ifndef GLZ_M
#define GLZ_M 4
#endif
typedef uint32_t glz_size_t;
typedef uint32_t glz_off_t;

int __box_glz_fsdecode(uint8_t k,
        int (*read)(void *ctx, uint32_t addr, void *buffer, size_t size),
        void *ctx,
        glz_off_t off,
        uint8_t *output, glz_size_t size) {
    // glz "stack"
    glz_off_t poff = 0;
    glz_size_t psize = 0;
    uint8_t x[2];

    while (size > 0) {
        // decode rice code
        uint_fast16_t rice = 0;
        while (true) {
            int err = read(ctx, off/8, x, 1);
            if (err) {
                return err;
            }
            if (!(1 & (x[0] >> (7-off%%8)))) {
                off += 1;
                break;
            }
            rice += 1;
            off += 1;
        }
        for (glz_off_t i = 0; i < k; i++) {
            int err = read(ctx, off/8, x, 1);
            if (err) {
                return err;
            }
            rice = (rice << 1) | (1 & (x[0] >> (7-off%%8)));
            off += 1;
        }

        // map through table
        int err = read(ctx, (9*rice)/8, x, 2);
        if (err) {
            return err;
        }
        rice = 0x1ff & (
            (x[0] << 8) |
            (x[1] << 0)) >> (7-(9*rice)%%8);

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
                    int err = read(ctx, off/8, x, 1);
                    if (err) {
                        return err;
                    }
                    n = (n << 1) | (1 & (x[0] >> (7-off%%8)));
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

BOX_LOAD = """
int __box_%(box)s_load(void) {
    extern uint32_t __box_%(box)s_%(memory)s_start;
    extern uint32_t __box_%(box)s_%(memory)s_end;

    // open file
    int32_t fd;
    int err = %(open_alias)s(&fd, "%(path)s", 0);
    if (err) {
        return err;
    }

    // load metadata?
    uint32_t size;
    ssize_t res = %(read_alias)s(fd, &size, sizeof(size));
    if (res < sizeof(size)) {
        if (res < 0) {
            return res;
        }
        return -ENOEXEC;
    }

    if (size > (uint8_t*)&__box_%(box)s_%(memory)s_end
            - (uint8_t*)&__box_%(box)s_%(memory)s_start) {
        // can't allow overwrites now can we
        return -ENOEXEC;
    }

    // load image
    res = %(read_alias)s(fd,
            (uint8_t*)&__box_%(box)s_%(memory)s_start,
            size);
    if (res < size) {
        if (res < 0) {
            return res;
        }
        return -ENOEXEC;
    }

    err = %(close_alias)s(fd);
    if (err) {
        return err;
    }

    return 0;
}
"""

BOX_LOAD_DECODE = """
struct __box_%(box)s_seekread {
    int32_t fd;
    uint32_t off;
};

static int __box_%(box)s_seekread(void *ctx,
        uint32_t addr, void *buffer, size_t size) {
    struct __box_%(box)s_seekread *s = ctx;
    addr += s->off;
    ssize_t res = %(seek_alias)s(s->fd, addr, 0);
    if (res < 0) {
        return res;
    }

    res = %(read_alias)s(s->fd, buffer, size);
    if (res < size) {
        if (res < 0) {
            return res;
        }
        return -EINVAL;
    }

    return 0;
}

// add checks for input size
int __box_%(box)s_load(void) {
    extern uint32_t __box_%(box)s_%(memory)s_start;
    extern uint32_t __box_%(box)s_%(memory)s_end;

    // open file
    int32_t fd;
    int err = %(open_alias)s(&fd, "%(path)s", 0);
    if (err) {
        return err;
    }

    // load metadata
    uint32_t x[2];
    ssize_t res = %(read_alias)s(fd, &x, sizeof(x));
    if (res < sizeof(x)) {
        if (res < 0) {
            return res;
        }
        return -ENOEXEC;
    }

    uint8_t k = 0xf & (x[0] >> 24);
    uint32_t off = 0x00ffffff & x[0];
    uint32_t size = x[1];
    if (size > (uint8_t*)&__box_%(box)s_%(memory)s_end
            - (uint8_t*)&__box_%(box)s_%(memory)s_start) {
        // can't allow overwrites now can we
        return -ENOEXEC;
    }

    // decompress region
    err = __box_glz_fsdecode(k,
            __box_%(box)s_seekread,
            &(struct __box_%(box)s_seekread){fd, 8},
            off,
            (uint8_t*)&__box_%(box)s_%(memory)s_start,
            size);
    if (err) {
        return err;
    }

    err = %(close_alias)s(fd);
    if (err) {
        return err;
    }

    return 0;
}
"""

# a little bit more complex when multiple regions are involved
BOX_LOAD_MULTI = """
int __box_%(box)s_load(void) {
    // open file
    int32_t fd;
    int err = %(open_alias)s(&fd, "%(path)s", 0);
    if (err) {
        return err;
    }

    // load metadata?
    uint32_t count;
    ssize_t res = %(read_alias)s(fd, &count, sizeof(count));
    if (res < sizeof(count)) {
        if (res < 0) {
            return res;
        }
        return -ENOEXEC;
    }

    if (count != %(n)d) {
        return -ENOEXEC;
    }

    uint32_t off = (1+%(n)d)*sizeof(uint32_t);
    for (uint32_t i = 0; i < %(n)d; i++) {
        // load metadata again
        uint32_t size;
        res = %(seek_alias)s(fd, (1+i)*sizeof(uint32_t), 0);
        if (res < 0) {
            return res;
        }
        res = %(read_alias)s(fd, &size, sizeof(size));
        if (res < sizeof(size)) {
            if (res < 0) {
                return res;
            }
            return -ENOEXEC;
        }

        if (size > __box_%(box)s_loadregions[i][1]
                - __box_%(box)s_loadregions[i][0]) {
            // can't allow overwrites now can we
            return -ENOEXEC;
        }

        // load region
        res = %(seek_alias)s(fd, off, 0);
        if (res < 0) {
            return res;
        }
        res = %(read_alias)s(fd, __box_%(box)s_loadregions[i][0], size);
        if (res < size) {
            if (res < 0) {
                return res;
            }
            return -ENOEXEC;
        }
        
        off += size;
    }

    err = %(close_alias)s(fd);
    if (err) {
        return err;
    }

    return 0;
}
"""

BOX_LOAD_DECODE_MULTI = """
struct __box_%(box)s_seekread {
    int32_t fd;
    uint32_t off;
};

static int __box_%(box)s_seekread(void *ctx,
        uint32_t addr, void *buffer, size_t size) {
    struct __box_%(box)s_seekread *s = ctx;
    addr += s->off;
    ssize_t res = %(seek_alias)s(s->fd, addr, 0);
    if (res < 0) {
        return res;
    }

    res = %(read_alias)s(s->fd, buffer, size);
    if (res < size) {
        if (res < 0) {
            return res;
        }
        return -EINVAL;
    }

    return 0;
}

int __box_%(box)s_load(void) {
    // open file
    int32_t fd;
    int err = %(open_alias)s(&fd, "%(path)s", 0);
    if (err) {
        return err;
    }

    // load metadata
    uint32_t x[2];
    ssize_t res = %(read_alias)s(fd, &x, sizeof(x));
    if (res < sizeof(x)) {
        if (res < 0) {
            return res;
        }
        return -ENOEXEC;
    }

    uint8_t k = 0xf & (x[0] >> 24);
    uint32_t off = 0x00ffffff & x[0];
    uint32_t count = x[1];
    if (count != %(n)d) {
        return -ENOEXEC;
    }

    for (uint32_t i = 0; i < %(n)d; i++) {
        // load metadata again
        res = %(seek_alias)s(fd, (1+i)*2*sizeof(uint32_t), 0);
        if (res < 0) {
            return res;
        }
        res = %(read_alias)s(fd, x, sizeof(x));
        if (res < sizeof(x)) {
            if (res < 0) {
                return res;
            }
            return -ENOEXEC;
        }

        uint32_t off = x[0];
        uint32_t size = x[1];
        if (size > __box_%(box)s_loadregions[i][1]
                - __box_%(box)s_loadregions[i][0]) {
            // can't allow overwrites now can we
            return -ENOEXEC;
        }

        // decompress region
        err = __box_glz_fsdecode(k,
                __box_%(box)s_seekread,
                &(struct __box_%(box)s_seekread){fd,
                    (1+%(n)d)*2*sizeof(uint32_t)},
                off,
                __box_%(box)s_loadregions[i][0],
                size);
        if (err) {
            return err;
        }
    }

    err = %(close_alias)s(fd);
    if (err) {
        return err;
    }

    return 0;
}
"""

@loaders.loader
class FSLoader(loaders.Loader):
    """
    A loader that loads boxes from an external filesystem using user
    provided __box_<box>_open, __box_<box>_read, __box_<box>_seek, and
    __box_<box>_close functions.
    """
    __argname__ = "fs"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser, **kwargs):
        parser.add_argument('--path',
            help='Path on the filesystem to load the box. Path limitations '
                'depend on the underlying filesystem.')
        parser.add_argument('--glz',
            help='Optional GLZ path. If provided, GLZ is used for '
                'decompressing the box when loaded. By default no compression '
                'is used.')
        parser.add_argument('--glz_flags', type=list,
            help='Add custom GLZ flags.')

    def __init__(self, path=None, glz=None, glz_flags=None):
        super().__init__()
        self._path = path
        assert self._path is not None, ("No path specified? "
            "Need --loader.fs.path=<path>.")
        self._glz = glz
        self._glz_flags = glz_flags or []

    def constraints(self, constraints):
        constraints['mode'].discard('p')
        constraints['mode'].add('w')

    def box_parent(self, parent, box):
        super().box_parent(parent, box)
        self._load_plug = parent.addexport(
            '__box_%s_load' % box.name, 'fn() -> err',
            target=parent.name, source=self.__argname__, weak=True)
        # need filesystem hooks
        self._open_hook = parent.addimport(
            '__box_%s_open' % box.name,
            # TODO const?
            'fn(mut i32 *fd, const i8 *path, u32 flags) -> err',
            target=parent.name, source=self.__argname__,
            doc="Open a file using a null-terminated path and flags.")
        self._close_hook = parent.addimport(
            '__box_%s_close' % box.name,
            'fn(i32 fd) -> err',
            target=parent.name, source=self.__argname__,
            doc="Close a file.")
        self._read_hook = parent.addimport(
            '__box_%s_read' % box.name,
            'fn(i32 fd, mut u8 *buffer, usize size) -> errsize',
            target=parent.name, source=self.__argname__,
            doc="Read bytes from a file.")
        self._seek_hook = parent.addimport(
            '__box_%s_seek' % box.name,
            'fn(i32 fd, usize off, u32 whence) -> errsize',
            target=parent.name, source=self.__argname__,
            doc="Seek in a file.")

    def box(self, box):
        super().box(box)
        # we also take care data implicitly
        box.addexport('__box_data_init', 'fn() -> void',
            target=box.name, source=self.__argname__, weak=True)

    def build_mk_prologue(self, output, box):
        super().build_mk_prologue(output, box)

        if self._glz:
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
        out.printf('$(TARGET): $(OBJ) $(ARCHIVES) $(BOXES) $(LDSCRIPT)')
        with out.indent():
            out.printf('$(CC) $(OBJ) $(BOXES) $(LDFLAGS) -o $@')

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
        out.printf('%%.box: %%.elf')
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
                out.printf(')')

    def build_parent_c_prologue(self, output, parent):
        super().build_parent_c_prologue(output, parent)

        output.decls.append(BOX_COMMON)

        if any(child.loader._glz
                for child in parent.boxes
                if child.loader == self):
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
        with output.pushattrs(
                path=self._path,
                open_alias=self._open_hook.link.export.alias,
                close_alias=self._close_hook.link.export.alias,
                read_alias=self._read_hook.link.export.alias,
                seek_alias=self._seek_hook.link.export.alias):

            if len(loadmemories) == 1:
                # if we only have one memory region (common), we can use
                # slightly less metadata
                if not self._glz:
                    output.decls.append(BOX_LOAD,
                        memory=loadmemories[0][0])
                else:
                    output.decls.append(BOX_LOAD_DECODE,
                        memory=loadmemories[0][0])
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

                if not self._glz:
                    out = output.decls.append(BOX_LOAD_MULTI,
                        n=len(loadmemories))
                else:
                    out = output.decls.append(BOX_LOAD_DECODE_MULTI,
                        n=len(loadmemories))

