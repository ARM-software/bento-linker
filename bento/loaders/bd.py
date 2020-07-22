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

int __box_glz_bddecode(uint8_t k,
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
#define BOX_%(BOX)s_BLOCK_SIZE %(block_size)d
#define BOX_%(BOX)s_READ_SIZE %(read_size)d

int __box_%(box)s_load(void) {
    extern uint32_t __box_%(box)s_%(memory)s_start;
    extern uint32_t __box_%(box)s_%(memory)s_end;

    // load metadata? We can use our RAM as a buffer here
    int err = %(alias)s(%(block)d, %(off)d,
            (uint8_t*)&__box_%(box)s_%(memory)s_start,
            __box_bd_max(sizeof(uint32_t), BOX_%(BOX)s_READ_SIZE));
    if (err) {
        return err;
    }

    size_t size = *(uint32_t*)(uint8_t*)&__box_%(box)s_%(memory)s_start;
    // align to read size
    size = __box_bd_alignup(size, BOX_%(BOX)s_READ_SIZE);
    if (size > (uint8_t*)&__box_%(box)s_%(memory)s_end
            - (uint8_t*)&__box_%(box)s_%(memory)s_start) {
        // can't allow overwrites now can we
        return -ENOEXEC;
    }

    // load image
    err = %(alias)s(%(block)d, %(off)d,
            (uint8_t*)&__box_%(box)s_%(memory)s_start,
            size);
    if (err) {
        return err;
    }

    return 0;
}
"""

BOX_LOAD_DECODE = """
#define BOX_%(BOX)s_BLOCK_SIZE %(block_size)d
#define BOX_%(BOX)s_BUFFER_SIZE %(buffer_size)d
#define BOX_%(BOX)s_READ_SIZE %(read_size)d

// bdread with buffer_size buffering, translation, and bounds checking
uint32_t __box_%(box)s_buffer_block;
uint32_t __box_%(box)s_buffer_off;
uint8_t __box_%(box)s_buffer[BOX_%(BOX)s_BUFFER_SIZE];
static int __box_%(box)s_buffer_read(void *ctx,
        uint32_t addr, void *buffer, size_t size) {
    uint32_t off = (uint32_t)ctx;
    addr = addr + off;
    if (addr + size > %(size)d) {
        return -EINVAL;
    }

    uint32_t block = addr / BOX_%(BOX)s_BLOCK_SIZE;
    off = addr - (block * BOX_%(BOX)s_BLOCK_SIZE);

    while (size > 0) {
        if (block == __box_%(box)s_buffer_block &&
                off >= __box_%(box)s_buffer_off &&
                off < __box_%(box)s_buffer_off + BOX_%(BOX)s_BUFFER_SIZE) {
            size_t delta = __box_bd_min(
                BOX_%(BOX)s_BUFFER_SIZE-(off-__box_%(box)s_buffer_off),
                size);
            memcpy(buffer,
                    &__box_%(box)s_buffer[off - __box_%(box)s_buffer_off],
                    delta);
            off += delta;
            size -= delta;
            continue;
        }

        // load buffer, first condition can't fail
        uint32_t nblock = block;
        uint32_t noff = __box_bd_aligndown(off, BOX_%(BOX)s_BUFFER_SIZE);
        int err = %(alias)s(nblock, noff,
                __box_%(box)s_buffer,
                BOX_%(BOX)s_BUFFER_SIZE);
        if (err) {
            return err;
        }
        __box_%(box)s_buffer_block = nblock;
        __box_%(box)s_buffer_off = noff;
    }

    return 0;
}

// add checks for input size
int __box_%(box)s_load(void) {
    extern uint32_t __box_%(box)s_%(memory)s_start;
    extern uint32_t __box_%(box)s_%(memory)s_end;
    // init buffer
    __box_%(box)s_buffer_block = -1;

    // load metadata
    uint32_t x[2];
    int err = __box_%(box)s_buffer_read(NULL, %(addr)d, x, sizeof(x));
    if (err) {
        return err;
    }

    uint8_t k = 0xf & (x[0] >> 24);
    uint32_t off = 0x00ffffff & x[0];
    uint32_t size = x[1];

    // align to read size
    size = __box_bd_alignup(size, BOX_%(BOX)s_READ_SIZE);
    if (size > (uint8_t*)&__box_%(box)s_%(memory)s_end
            - (uint8_t*)&__box_%(box)s_%(memory)s_start) {
        // can't allow overwrites now can we
        return -ENOEXEC;
    }

    // decompress region
    return __box_glz_bddecode(k,
            __box_%(box)s_buffer_read, (void*)(%(addr)d + 8),
            off,
            (uint8_t*)&__box_%(box)s_%(memory)s_start,
            size);
}
"""

# a little bit more complex when multiple regions are involved
BOX_LOAD_MULTI = """
#define BOX_%(BOX)s_BLOCK_SIZE %(block_size)d
#define BOX_%(BOX)s_BUFFER_SIZE %(buffer_size)d
#define BOX_%(BOX)s_READ_SIZE %(read_size)d

// bdread with buffer_size buffering, translation, and bounds checking
uint32_t __box_%(box)s_buffer_block;
uint32_t __box_%(box)s_buffer_off;
uint8_t __box_%(box)s_buffer[BOX_%(BOX)s_BUFFER_SIZE];
static int __box_%(box)s_buffer_read(void *ctx,
        uint32_t addr, void *buffer, size_t size) {
    uint32_t off = (uint32_t)ctx;
    addr = addr + off;
    if (addr + size > %(size)d) {
        return -EINVAL;
    }

    uint32_t block = addr / BOX_%(BOX)s_BLOCK_SIZE;
    uint32_t off = addr - (block * BOX_%(BOX)s_BLOCK_SIZE);

    while (size > 0) {
        if (block == __box_%(box)s_buffer_block &&
                off >= __box_%(box)s_buffer_off &&
                off < __box_%(box)s_buffer_off + BOX_%(BOX)s_BUFFER_SIZE) {
            size_t delta = __box_bd_min(
                BOX_%(BOX)s_BUFFER_SIZE-(off-__box_%(box)s_buffer_off),
                size);
            memcpy(buffer,
                    &__box_%(box)s_buffer[off - __box_%(box)s_buffer_off],
                    delta);
            off += delta;
            size -= delta;
            continue;
        }

        // load buffer, first condition can't fail
        uint32_t nblock = block;
        uint32_t noff = __box_bd_aligndown(off, BOX_%(BOX)s_BUFFER_SIZE);
        int err = %(alias)s(nblock, noff,
                __box_%(box)s_buffer,
                BOX_%(BOX)s_BUFFER_SIZE);
        if (err) {
            return err;
        }
        __box_%(box)s_buffer_block = nblock;
        __box_%(box)s_buffer_off = noff;
    }

    return 0;
}

int __box_%(box)s_load(void) {
    // init buffer
    __box_%(box)s_buffer_block = -1;

    // load metadata?
    uint32_t count;
    int err = __box_%(box)s_buffer_read(NULL, %(addr)d,
            &count, sizeof(count));
    if (err) {
        return err;
    }

    if (count != %(n)d) {
        return -ENOEXEC;
    }

    uint32_t off = (1+%(n)d)*sizeof(uint32_t);
    for (uint32_t i = 0; i < %(n)d; i++) {
        // load metadata again
        uint32_t size;
        int err = __box_%(box)s_buffer_read(
                NULL, %(addr)d+(1+i)*sizeof(uint32_t),
                &size, sizeof(size));
        if (err) {
            return err;
        }

        if (size > __box_%(box)s_loadregions[i][1]
                - __box_%(box)s_loadregions[i][0]) {
            // can't allow overwrites now can we
            return -ENOEXEC;
        }

        // load region
        err = __box_%(box)s_buffer_read(NULL, off,
                __box_%(box)s_loadregions[i][0], size);
        if (err) {
            return err;
        }

        off += size;
    }

    return 0;
}
"""

BOX_LOAD_DECODE_MULTI = """
#define BOX_%(BOX)s_BLOCK_SIZE %(block_size)d
#define BOX_%(BOX)s_BUFFER_SIZE %(buffer_size)d
#define BOX_%(BOX)s_READ_SIZE %(read_size)d

// bdread with buffer_size buffering, translation, and bounds checking
uint32_t __box_%(box)s_buffer_block;
uint32_t __box_%(box)s_buffer_off;
uint8_t __box_%(box)s_buffer[BOX_%(BOX)s_BUFFER_SIZE];
static int __box_%(box)s_buffer_read(void *ctx,
        uint32_t addr, void *buffer, size_t size) {
    uint32_t off = (uint32_t)ctx;
    addr = addr + off;
    if (addr + size > %(size)d) {
        return -EINVAL;
    }

    uint32_t block = addr / BOX_%(BOX)s_BLOCK_SIZE;
    off = addr - (block * BOX_%(BOX)s_BLOCK_SIZE);

    while (size > 0) {
        if (block == __box_%(box)s_buffer_block &&
                off >= __box_%(box)s_buffer_off &&
                off < __box_%(box)s_buffer_off + BOX_%(BOX)s_BUFFER_SIZE) {
            size_t delta = __box_bd_min(
                BOX_%(BOX)s_BUFFER_SIZE-(off-__box_%(box)s_buffer_off),
                size);
            memcpy(buffer,
                    &__box_%(box)s_buffer[off - __box_%(box)s_buffer_off],
                    delta);
            off += delta;
            size -= delta;
            continue;
        }

        // load buffer, first condition can't fail
        uint32_t nblock = block;
        uint32_t noff = __box_bd_aligndown(off, BOX_%(BOX)s_BUFFER_SIZE);
        int err = %(alias)s(nblock, noff,
                __box_%(box)s_buffer,
                BOX_%(BOX)s_BUFFER_SIZE);
        if (err) {
            return err;
        }
        __box_%(box)s_buffer_block = nblock;
        __box_%(box)s_buffer_off = noff;
    }

    return 0;
}

int __box_%(box)s_load(void) {
    // init buffer
    __box_%(box)s_buffer_block = -1;

    // load metadata
    uint32_t x[2];
    int err = __box_%(box)_buffer_read(NULL, %(addr)d, x, sizeof(x));
    if (err) {
        return err;
    }

    uint8_t k = 0xf & (x[0] >> 24);
    uint32_t off = 0x00ffffff & x[0];
    uint32_t count = x[1];
    if (count != %(n)d) {
        return -ENOEXEC;
    }

    for (uint32_t i = 0; i < %(n)d; i++) {
        // load metadata again
        int err = __box_%(box)s_buffer_read(
                NULL, %(addr)d+(1+i)*2*sizeof(uint32_t),
                x, sizeof(x));
        if (err) {
            return err;
        }

        uint32_t off = x[0];
        uint32_t size = x[1];
        if (size > __box_%(box)s_loadregions[i][1]
                - __box_%(box)s_loadregions[i][0]) {
            // can't allow overwrites now can we
            return -ENOEXEC;
        }

        // load region
        err = __box_%(box)s_buffer_read(NULL, off,
                __box_%(box)s_loadregions[i][0], size);
        if (err) {
            return err;
        }

        // decompress region
        err = __box_glz_bddecode(k,
                __box_%(box)s_buffer_read,
                (void*)(%(addr)d + (1+%(n)d)*2*sizeof(uint32_t)),
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
class BDLoader(loaders.Loader):
    """
    A loader that loads boxes from an external block device using a user
    provided __box_<box>_bdread function.
    """
    __argname__ = "bd"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser, **kwargs):
        parser.add_nestedparser('--region', Region,
            help='Region on the block device to store the box. Appropriate '
                'padding is added to make sure the box can be loaded based on '
                'the specified read_size and block_size.')
        parser.add_argument('--read_size', type=int,
            help='Minimum read size on the block device in bytes. Reads may '
                'be a multiple of this size. Defaults to 1 byte.')
        parser.add_argument('--buffer_size', type=int,
            help='Buffer size to use for reading from the block device. '
                'Defaults to max(read_size, 16).')
        parser.add_argument('--block_size', type=int,
            help='Block size on the block device in bytes.')
        parser.add_argument('--glz',
            help='Optional GLZ path. If provided, GLZ is used for '
                'decompressing the box when loaded. By default no compression '
                'is used.')
        parser.add_argument('--glz_flags', type=list,
            help='Add custom GLZ flags.')

    def __init__(self, region=None,
            read_size=None, buffer_size=None, block_size=None,
            glz=None, glz_flags=None):
        super().__init__()
        self._region = Region(**region.__dict__)
        assert self._region, ("No block device region specified? "
            "Need --loader.bd.region=<region>.")
        self._read_size = read_size or 1
        self._buffer_size = buffer_size or max(self._read_size, 16)
        assert self._buffer_size % self._read_size == 0, (
            "buffer_size not aligned to read_size?")
        self._block_size = block_size
        assert self._block_size, ("No block size specified? "
            "Need --loader.bd.block_size=<block_size>.")
        assert self._block_size % self._buffer_size == 0, (
            "block_size not aligned to buffer_size?")
        self._glz = glz
        self._glz_flags = glz_flags or []

    def constraints(self, constraints):
        constraints['mode'].discard('p')
        constraints['mode'].add('w')

    def box_parent(self, parent, box):
        super().box_parent(parent, box)
        self._load_plug = parent.addexport(
            '__box_%s_load' % box.name, 'fn() -> err',
            scope=parent.name, source=self.__argname__, weak=True)
        # need block device hook
        self._bdread_hook = parent.addimport(
            '__box_%s_bdread' % box.name,
            'fn(u32 block, u32 off, mut u8 *buffer, usize size) -> err',
            scope=parent.name, source=self.__argname__,
            doc="Read from block device using a block number and offset. "
                "Must be in multiples of the read_size.")

    def box(self, box):
        super().box(box)
        # we also take care data implicitly
        box.addexport('__box_data_init', 'fn() -> void',
            scope=box.name, source=self.__argname__, weak=True)

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
                alias=self._bdread_hook.link.export.alias,
                addr=self._region.addr,
                size=self._region.size,
                block=self._region.addr // self._block_size,
                off=self._region.addr - (
                    (self._region.addr // self._block_size) * self._block_size),
                block_size=self._block_size,
                buffer_size=self._buffer_size,
                read_size=self._read_size):

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

