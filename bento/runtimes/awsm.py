
import itertools as it
import math
from .. import argstuff
from .. import runtimes
from ..box import Fn, Section, Region, Import, Export
from ..glue.error_glue import ErrorGlue
from ..glue.write_glue import WriteGlue
from ..glue.abort_glue import AbortGlue
from ..glue.heap_glue import HeapGlue
from ..outputs import OutputBlob


BOUNDS_CHECK_BRANCH = """
/// conditional branch memory implementation ///
extern uint8_t __memory[];
extern uint8_t __memory_start;
extern uint8_t __memory_end;
#define MEMORY_SIZE %(memory_size)d

__attribute__((always_inline))
void *to_ptr(uint32_t off) {
    return &__memory[off];
}

__attribute__((always_inline))
uint32_t from_ptr(const void *ptr) {
    return (uint8_t*)ptr - __memory;
}

__attribute__((always_inline))
int8_t get_i8(uint32_t off) {
    if (__builtin_expect(off > MEMORY_SIZE - sizeof(int8_t), false)) {
        __box_abort(-EFAULT);
    }

    return *(int8_t*)to_ptr(off);
}

__attribute__((always_inline))
int16_t get_i16(uint32_t off) {
    if (__builtin_expect(off > MEMORY_SIZE - sizeof(int16_t), false)) {
        __box_abort(-EFAULT);
    }

    return *(int16_t*)to_ptr(off);
}

__attribute__((always_inline))
int32_t get_i32(uint32_t off) {
    if (__builtin_expect(off > MEMORY_SIZE - sizeof(int32_t), false)) {
        __box_abort(-EFAULT);
    }

    return *(int32_t*)to_ptr(off);
}

__attribute__((always_inline))
int64_t get_i64(uint32_t off) {
    if (__builtin_expect(off > MEMORY_SIZE - sizeof(int64_t), false)) {
        __box_abort(-EFAULT);
    }

    return *(int64_t*)to_ptr(off);
}

__attribute__((always_inline))
float get_f32(uint32_t off) {
    if (__builtin_expect(off > MEMORY_SIZE - sizeof(float), false)) {
        __box_abort(-EFAULT);
    }

    return *(float*)to_ptr(off);
}

__attribute__((always_inline))
double get_f64(uint32_t off) {
    if (__builtin_expect(off > MEMORY_SIZE - sizeof(double), false)) {
        __box_abort(-EFAULT);
    }

    return *(double*)to_ptr(off);
}

__attribute__((always_inline))
void set_i8(uint32_t off, int8_t v) {
    if (__builtin_expect(off > MEMORY_SIZE - sizeof(int8_t), false)) {
        __box_abort(-EFAULT);
    }

    *(int8_t*)to_ptr(off) = v;
}

__attribute__((always_inline))
void set_i16(uint32_t off, int16_t v) {
    if (__builtin_expect(off > MEMORY_SIZE - sizeof(int16_t), false)) {
        __box_abort(-EFAULT);
    }

    *(int16_t*)to_ptr(off) = v;
}

__attribute__((always_inline))
void set_i32(uint32_t off, int32_t v) {
    if (__builtin_expect(off > MEMORY_SIZE - sizeof(int32_t), false)) {
        __box_abort(-EFAULT);
    }

    *(int32_t*)to_ptr(off) = v;
}

__attribute__((always_inline))
void set_i64(uint32_t off, int64_t v) {
    if (__builtin_expect(off > MEMORY_SIZE - sizeof(int64_t), false)) {
        __box_abort(-EFAULT);
    }

    *(int64_t*)to_ptr(off) = v;
}

__attribute__((always_inline))
void set_f32(uint32_t off, float v) {
    if (__builtin_expect(off > MEMORY_SIZE - sizeof(float), false)) {
        __box_abort(-EFAULT);
    }

    *(float*)to_ptr(off) = v;
}

__attribute__((always_inline))
void set_f64(uint32_t off, double v) {
    if (__builtin_expect(off > MEMORY_SIZE - sizeof(double), false)) {
        __box_abort(-EFAULT);
    }

    *(double*)to_ptr(off) = v;
}

__attribute__((always_inline))
uint8_t *get_memory_ptr_for_runtime(uint32_t off, uint32_t bounds) {
    if (__builtin_expect(off > MEMORY_SIZE - bounds, false)) {
        __box_abort(-EFAULT);
    }

    return to_ptr(off);
}
"""

BOUNDS_CHECK_WRAP = """
/// conditional branch memory implementation ///
extern uint8_t __memory[];
extern uint8_t __memory_start;
extern uint8_t __memory_end;
#define MEMORY_SIZE %(memory_size)d

__attribute__((always_inline))
void *to_ptr(uint32_t off) {
    return &__memory[off];
}

__attribute__((always_inline))
uint32_t from_ptr(const void *ptr) {
    return (uint8_t*)ptr - __memory;
}

__attribute__((always_inline))
int8_t get_i8(uint32_t off) {
    off = off %% MEMORY_SIZE;
    return *(int8_t*)to_ptr(off);
}

__attribute__((always_inline))
int16_t get_i16(uint32_t off) {
    off = off %% MEMORY_SIZE;
    return *(int16_t*)to_ptr(off);
}

__attribute__((always_inline))
int32_t get_i32(uint32_t off) {
    off = off %% MEMORY_SIZE;
    return *(int32_t*)to_ptr(off);
}

__attribute__((always_inline))
int64_t get_i64(uint32_t off) {
    off = off %% MEMORY_SIZE;
    return *(int64_t*)to_ptr(off);
}

__attribute__((always_inline))
float get_f32(uint32_t off) {
    off = off %% MEMORY_SIZE;
    return *(float*)to_ptr(off);
}

__attribute__((always_inline))
double get_f64(uint32_t off) {
    off = off %% MEMORY_SIZE;
    return *(double*)to_ptr(off);
}

__attribute__((always_inline))
void set_i8(uint32_t off, int8_t v) {
    off = off %% MEMORY_SIZE;
    *(int8_t*)to_ptr(off) = v;
}

__attribute__((always_inline))
void set_i16(uint32_t off, int16_t v) {
    off = off %% MEMORY_SIZE;
    *(int16_t*)to_ptr(off) = v;
}

__attribute__((always_inline))
void set_i32(uint32_t off, int32_t v) {
    off = off %% MEMORY_SIZE;
    *(int32_t*)to_ptr(off) = v;
}

__attribute__((always_inline))
void set_i64(uint32_t off, int64_t v) {
    off = off %% MEMORY_SIZE;
    *(int64_t*)to_ptr(off) = v;
}

__attribute__((always_inline))
void set_f32(uint32_t off, float v) {
    off = off %% MEMORY_SIZE;
    *(float*)to_ptr(off) = v;
}

__attribute__((always_inline))
void set_f64(uint32_t off, double v) {
    off = off %% MEMORY_SIZE;
    *(double*)to_ptr(off) = v;
}

__attribute__((always_inline))
uint8_t *get_memory_ptr_for_runtime(uint32_t off, uint32_t bounds) {
    if (__builtin_expect(off > MEMORY_SIZE - bounds, false)) {
        __box_abort(-EFAULT);
    }

    return to_ptr(off);
}
"""

BOUNDS_CHECK_NONE = """
/// conditional branch memory implementation ///
extern uint8_t __memory[];
extern uint8_t __memory_start;
extern uint8_t __memory_end;
#define MEMORY_SIZE %(memory_size)d

__attribute__((always_inline))
void *to_ptr(uint32_t off) {
    return &__memory[off];
}

__attribute__((always_inline))
uint32_t from_ptr(const void *ptr) {
    return (uint8_t*)ptr - __memory;
}

__attribute__((always_inline))
int8_t get_i8(uint32_t off) {
    return *(int8_t*)to_ptr(off);
}

__attribute__((always_inline))
int16_t get_i16(uint32_t off) {
    return *(int16_t*)to_ptr(off);
}

__attribute__((always_inline))
int32_t get_i32(uint32_t off) {
    return *(int32_t*)to_ptr(off);
}

__attribute__((always_inline))
int64_t get_i64(uint32_t off) {
    return *(int64_t*)to_ptr(off);
}

__attribute__((always_inline))
float get_f32(uint32_t off) {
    return *(float*)to_ptr(off);
}

__attribute__((always_inline))
double get_f64(uint32_t off) {
    return *(double*)to_ptr(off);
}

__attribute__((always_inline))
void set_i8(uint32_t off, int8_t v) {
    *(int8_t*)to_ptr(off) = v;
}

__attribute__((always_inline))
void set_i16(uint32_t off, int16_t v) {
    *(int16_t*)to_ptr(off) = v;
}

__attribute__((always_inline))
void set_i32(uint32_t off, int32_t v) {
    *(int32_t*)to_ptr(off) = v;
}

__attribute__((always_inline))
void set_i64(uint32_t off, int64_t v) {
    *(int64_t*)to_ptr(off) = v;
}

__attribute__((always_inline))
void set_f32(uint32_t off, float v) {
    *(float*)to_ptr(off) = v;
}

__attribute__((always_inline))
void set_f64(uint32_t off, double v) {
    *(double*)to_ptr(off) = v;
}

__attribute__((always_inline))
uint8_t *get_memory_ptr_for_runtime(uint32_t off, uint32_t bounds) {
    if (__builtin_expect(off > MEMORY_SIZE - bounds, false)) {
        __box_abort(-EFAULT);
    }

    return to_ptr(off);
}
"""

BOUNDS_CHECKS = {
    'none':     BOUNDS_CHECK_NONE,
    'wrap':     BOUNDS_CHECK_WRAP,
    'branch':   BOUNDS_CHECK_BRANCH,
}

COMMON = """
// linked from aWsm
const uint32_t memory_size = MEMORY_SIZE;

void expand_memory(void) {
    // not supported
    __box_abort(-ENOMEM);
}

struct table_entry {
    uint32_t type_id;
    void *func_ptr;
};

extern struct table_entry __table[];
#define TABLE_COUNT %(table_size)d

__attribute__((always_inline))
char *get_function_from_table(uint32_t idx, uint32_t type_id) {
    if (__builtin_expect(idx >= TABLE_COUNT, false)) {
        __box_abort(-EFAULT);
    }

    struct table_entry f = __table[idx];

    if (__builtin_expect(f.type_id != type_id || !f.func_ptr, false)) {
        __box_abort(-EFAULT);
    }

    return f.func_ptr;
}

void add_function_to_table(uint32_t idx, uint32_t type_id, void *func_ptr) {
    if (__builtin_expect(idx >= TABLE_COUNT, false)) {
        __box_abort(-EFAULT);
    }

    __table[idx].type_id = type_id;
    __table[idx].func_ptr = func_ptr;
}

void clear_table(void) {
    memset(__table, 0, TABLE_COUNT*sizeof(struct table_entry));
}

// TODO remove the need for this?
__attribute__((alias("__wrap_printf")))
ssize_t printf_(const char *format, ...);

__attribute__((alias("__wrap_abort")))
__attribute__((noreturn))
void abort_(void);

__attribute__((alias("env___box_abort")))
void __box_abort(int err);

__attribute__((alias("env___box_write")))
ssize_t __box_write(int32_t fd, const void *buffer, size_t size);

__attribute__((alias("env___box_flush")))
int __box_flush(int32_t fd);

// glue that awsm may emit
__attribute__((weak)) void populate_table(void) {}
__attribute__((weak)) void populate_globals(void) {}
__attribute__((weak)) void populate_memory(void) {}
__attribute__((weak)) void wasmf___wasm_call_ctors(void) {}

// data stack manipulation
uint8_t *__box_datasp = &__memory_start;

void *__box_push(size_t size) {
    // we maintain a separate stack in the wasm memory space,
    // sharing the stack space of the wasm-side libc
    uint8_t *psp = __box_datasp;
    if (psp + size > &__memory_end) {
        return NULL;
    }

    __box_datasp = psp + size;
    return psp + size;
}

void __box_pop(size_t size) {
    if (__builtin_expect(__box_datasp - size < &__memory_start, false)) {
        __box_abort(-EFAULT);
    }
    __box_datasp -= size;
}
"""

@runtimes.runtime
class aWsmRuntime(
        ErrorGlue,
        WriteGlue,
        AbortGlue,
        HeapGlue,
        runtimes.Runtime):
    """
    A bento-box runtime using aWsm, an ahead-of-time compiler for wasm
    """
    __argname__ = "awsm"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser, **kwargs):
        # TODO rename this?
        parser.add_argument('--bounds_check',
            choices=['none', 'wrap', 'branch'],
            help="Bounds checking method for sanitizing load/stores. Must be "
                "one of {%(choices)s}. `branch` conditionally checks for "
                "out-of-bounds and faults, while `wrap` provides a faster "
                "mask to addresses but does not fault. Defaults to `branch`.")
        parser.add_nestedparser('--memory', Section,
            help="Description of the memory section that backs the "
                "WebAssembly linear memory. Defaults to 1 page (64KiB).")
        parser.add_nestedparser('--table', Section,
            help="Description of the table section tbat backs the "
                "indirect function pointer table used by WebAssembly. "
                "Defaults to 64 entries (8*6 bytes).")
        parser.add_nestedparser('--jumptable', Section)
        parser.add_argument('--no_longjmp', type=bool,
            help="Do not use longjmp for error recovery. longjmp adds a small "
                "cost to every box entry point. --no_longjmp disables longjmp "
                "and forces any unhandled aborts to halt. Note this has no "
                "affetc if an explicit __box_<box>_abort hook is provided.")

    def __init__(self, bounds_check=None,
            memory=None, table=None,
            jumptable=None, no_longjmp=None):
        super().__init__()
        self._bounds_check = bounds_check or 'branch'
        self._memory = Section('memory', **memory.__dict__)
        if memory.size is None:
            self._memory.size = 64*1024
        self._table = Section('table', **table.__dict__)
        if table.size is None:
            self._table.size = 64*8
        self._jumptable = Section('jumptable', **jumptable.__dict__)
        self._no_longjmp = no_longjmp or False

    def box_parent(self, parent, box):
        self._load_hook = parent.addimport(
            '__box_%s_load' % box.name, 'fn() -> err',
            scope=parent.name, source=self.__argname__,
            doc="Called to load the box during init. Normally provided "
                "by the loader but can be overriden.")
        self._abort_hook = parent.addimport(
            '__box_%s_abort' % box.name, 'fn(err err) -> noreturn',
            scope=parent.name, source=self.__argname__, weak=True,
            doc="Called when this box aborts, either due to an illegal "
                "memory access or other failure. the error code is "
                "provided as an argument.")
        self._write_hook = parent.addimport(
            '__box_%s_write' % box.name,
            'fn(i32, const u8[size], usize size) -> errsize',
            scope=parent.name, source=self.__argname__, weak=True,
            doc="Override __box_write for this specific box.")
        self._flush_hook = parent.addimport(
            '__box_%s_flush' % box.name,
            'fn(i32) -> err',
            scope=parent.name, source=self.__argname__, weak=True,
            doc="Override __box_flush for this specific box.")
        super().box_parent(parent, box)

    def box(self, box):
        super().box(box)
        self._memory.alloc(box, 'rw')
        self._table.alloc(box, 'rw')
        self._jumptable.alloc(box, 'rp')
        box.pushattrs(
            memory_size=self._memory.size,
            table_size=self._table.size)

        # plugs
        self._abort_plug = box.addexport(
            '__box_abort', 'fn(err) -> noreturn',
            scope=box.name, source=self.__argname__, weak=True)
        self._write_plug = box.addexport(
            '__box_write', 'fn(i32, const u8[size], usize size) -> errsize',
            scope=box.name, source=self.__argname__, weak=True)
        self._flush_plug = box.addexport(
            '__box_flush', 'fn(i32) -> err',
            scope=box.name, source=self.__argname__, weak=True)

    def _parentimports(self, parent, box):
        """
        Get imports that need linking.
        Yields import, needsinit.
        """
        # implicit imports
        yield Import(
            '__box_%s_postinit' % box.name,
            'fn(const u32*) -> err32',
            source=self.__argname__), False
        yield Import(
            '__box_%s_push' % box.name,
            'fn(usize) -> mut u8*',
            source=self.__argname__), False
        yield Import(
            '__box_%s_pop' % box.name,
            'fn(usize) -> void',
            source=self.__argname__), False

        # imports that need linking
        for import_ in parent.imports:
            if import_.link and import_.link.export.box == box:
                yield import_.postbound(), box.init == 'lazy'

    def _parentexports(self, parent, box):
        """
        Get exports that need linking
        Yields export, needswrapper.
        """
        # implicit exports
        yield Export(
            '__box_%s_abort' % box.name,
            'fn(err) -> noreturn',
            source=self.__argname__), False
        yield Export(
            '__box_%s_write' % box.name,
            'fn(i32, const u8*, usize) -> errsize',
            source=self.__argname__), False
        yield Export(
            '__box_%s_flush' % box.name,
            'fn(i32) -> err',
            source=self.__argname__), False

        # exports that need linking
        for export in parent.exports:
            if any(link.import_.box == box for link in export.links):
                yield export.prebound(), len(export.boundargs) > 0

    def _imports(self, box):
        """
        Get imports that need linking.
        Yields import.
        """
        # implicit imports
        yield Import(
            '__box_abort',
            'fn(err) -> noreturn',
            source=self.__argname__)
        yield Import(
            '__box_write',
            'fn(i32, const u8[size], usize size) -> errsize',
            source=self.__argname__)
        yield Export(
            '__box_flush',
            'fn(i32) -> err',
            source=self.__argname__)

        # imports that need linking
        for import_ in box.imports:
            if import_.link and import_.link.export.box != box:
                yield import_.postbound()

    def _exports(self, box):
        """
        Get exports that need linking.
        Yields export, needswrapper.
        """
        # implicit exports
        yield Export(
            '__box_init', 'fn() -> err32',
            source=self.__argname__), False

        # exports that need linking
        for export in box.exports:
            if export.scope != box:
                yield export.prebound(), (
                    len(export.boundargs) > 0 or
                    any(arg.isptr() for arg in export.args))

    @staticmethod
    def repr_wasmfarg(arg, name=None):
        name = name if name is not None else arg.name
        return ''.join([
            'uint32_t'  if arg.isptr() else
            'int64_t'   if arg.prim() == 'err64' else
            'int32_t'   if arg.prim().startswith('err') else
            'int32_t'   if arg.prim() == 'isize' else
            'uint32_t'  if arg.prim() == 'usize' else
            'int%s_t'  % arg.prim()[1:] if arg.prim().startswith('i') else
            'uint%s_t' % arg.prim()[1:] if arg.prim().startswith('u') else
            '???',
            ' ' if name else '',
            name if name else ''])

    @classmethod
    def repr_wasmf(cls, fn, name=None, attrs=[]):
        return ''.join(it.chain(
            (attr + ('\n' if attr.startswith('__') else ' ')
                for attr in it.chain(
                    (['__attribute__((noreturn))']
                        if fn.isnoreturn() and (
                            name is None or '*' not in name) else
                        []) +
                    attrs)), [
            '%s ' % cls.repr_wasmfarg(fn.rets[0], '') if fn.rets else
            'void ',
            name if name is not None else fn.alias,
            '(',
            ', '.join(cls.repr_wasmfarg(arg, name)
                for arg, name in zip(fn.args, fn.argnames()))
            if fn.args else
            'void',
            ')']))

    def build_parent_c(self, output, parent, box):
        super().build_parent_c(output, parent, box)

        out = output.decls.append()
        out.printf('//// %(box)s state ////')
        out.printf('bool __box_%(box)s_initialized = false;')
        if not self._abort_hook.link and not self._no_longjmp:
            out.printf('jmp_buf *__box_%(box)s_jmpbuf = NULL;')
        out.printf('extern uint32_t __box_%(box)s_jumptable[];')
        out.printf('#define __box_%(box)s_exportjumptable '
            '__box_%(box)s_jumptable')

        output.decls.append('//// %(box)s exports ////')

        for i, (import_, needsinit) in enumerate(
                self._parentimports(parent, box)):
            out = output.decls.append(
                fn=output.repr_fn(import_),
                fnptr=output.repr_fnptr(import_.prebound(), ''),
                i=i)
            out.printf('%(fn)s {')
            with out.indent():
                # inject lazy-init?
                if needsinit:
                    out.printf('if (!__box_%(box)s_initialized) {')
                    with out.indent():
                        out.printf('int err = __box_%(box)s_init();')
                        out.printf('if (err) {')
                        with out.indent():
                            if import_.isfalible():
                                out.printf('return err;')
                            else:
                                out.printf('__box_abort(err);')
                        out.printf('}')
                    out.printf('}')
                    out.printf()
                # use longjmp?
                if (import_.isfalible() and
                        not self._abort_hook.link and
                        not self._no_longjmp):
                    with out.pushattrs(
                            pjmpbuf=import_.uniquename('pjmpbuf'),
                            jmpbuf=import_.uniquename('jmpbuf'),
                            err=import_.uniquename('err')):
                        out.printf('jmp_buf *%(pjmpbuf)s = '
                            '__box_%(box)s_jmpbuf;')
                        out.printf('jmp_buf %(jmpbuf)s;')
                        out.printf('__box_%(box)s_jmpbuf = &%(jmpbuf)s;')
                        out.printf('int %(err)s = setjmp(%(jmpbuf)s);')
                        out.printf('if (%(err)s) {')
                        with out.indent():
                            out.printf('__box_%(box)s_jmpbuf = %(pjmpbuf)s;')
                            out.printf('return %(err)s;')
                        out.printf('}')
                # jump to jumptable entry
                out.printf('%(return_)s((%(fnptr)s)\n'
                    '        __box_%(box)s_exportjumptable[%(i)d])(%(args)s);',
                    return_=('return ' if import_.rets else '')
                        if not (import_.isfalible() and
                            not self._abort_hook.link and
                            not self._no_longjmp) else
                        ('%s = ' % output.repr_arg(import_.rets[0],
                                import_.retname())
                            if import_.rets else ''),
                    args=', '.join(map(str, import_.argnamesandbounds())))
                if import_.isnoreturn():
                    # kinda wish we could apply noreturn to C types...
                    out.printf('__builtin_unreachable();')
                # use longjmp?
                if (import_.isfalible() and
                        not self._abort_hook.link and
                        not self._no_longjmp):
                    with out.pushattrs(
                            pjmpbuf=import_.uniquename('pjmpbuf')):
                        out.printf('__box_%(box)s_jmpbuf = %(pjmpbuf)s;')
                        if import_.rets:
                            out.printf('return %(ret)s;',
                                ret=import_.retname())
            out.printf('}')
            
        output.decls.append('//// %(box)s imports ////')

        # redirect hooks if necessary
        if not self._abort_hook.link:
            if not self._no_longjmp:
                # use longjmp to recover from explicit aborts
                output.includes.append('<setjmp.h>')
                out = output.decls.append(
                    fn=output.repr_fn(self._abort_hook,
                        self._abort_hook.name))
                out.printf('%(fn)s {')
                with out.indent():
                    out.printf('__box_%(box)s_initialized = false;')
                    out.printf('if (__box_%(box)s_jmpbuf) {')
                    with out.indent():
                        out.printf('longjmp(*__box_%(box)s_jmpbuf, err);')
                    out.printf('} else {')
                    with out.indent():
                        out.printf('__box_abort(err);')
                    out.printf('}')
                out.printf('}')
            else:
                # just redirect to parent's __box_abort
                out = output.decls.append(
                    abort_hook=self._abort_hook.name,
                    doc='redirect %(abort_hook)s -> __box_abort')
                out.printf('#define %(abort_hook)s __box_abort')

        if not self._write_hook.link:
            out = output.decls.append(
                write_hook=self._write_hook.name,
                doc='redirect %(write_hook)s -> __box_write')
            out.printf('#define %(write_hook)s __box_write')

        if not self._flush_hook.link:
            out = output.decls.append(
                flush_hook=self._flush_hook.name,
                doc='redirect %(flush_hook)s -> __box_flush')
            out.printf('#define %(flush_hook)s __box_flush')

        # wrappers?
        for export in (export
                for export, needswrapper in self._parentexports(parent, box)
                if needswrapper):
            out = output.decls.append(
                fn=output.repr_fn(
                    export.postbound(),
                    name='__box_%(box)s_export_%(alias)s'),
                alias=export.alias)
            out.printf('%(fn)s {')
            with out.indent():
                out.printf('%(return_)s%(alias)s(%(args)s);',
                    return_='return ' if import_.rets else '',
                    args=', '.join(map(str, export.argnamesandbounds())))
            out.printf('}')

        # import jumptable
        out = output.decls.append()
        out.printf('const uint32_t __box_%(box)s_importjumptable[] = {')
        with out.indent():
            for export, needswrapper in self._parentexports(parent, box):
                out.printf('(uint32_t)%(prefix)s%(alias)s,',
                    prefix='__box_%(box)s_export_' if needswrapper else '',
                    alias=export.alias)
        out.printf('};')

        # init
        output.decls.append('//// %(box)s init ////')
        out = output.decls.append()
        out.printf('int __box_%(box)s_init(void) {')
        with out.indent():
            out.printf('int err;')
            out.printf('if (__box_%(box)s_initialized) {')
            with out.indent():
                out.printf('return 0;')
            out.printf('}')
            out.printf()
            if box.roommates:
                out.printf('// bring down any overlapping boxes')
            for i, roommate in enumerate(box.roommates):
                with out.pushattrs(roommate=roommate.name):
                    out.printf('extern int __box_%(roommate)s_clobber(void);')
                    out.printf('err = __box_%(roommate)s_clobber();')
                    out.printf('if (err) {')
                    with out.indent():
                        out.printf('return err;')
                    out.printf('}')
                    out.printf()
            out.printf('// load the box if unloaded')
            out.printf('err = __box_%(box)s_load();')
            out.printf('if (err) {')
            with out.indent():
                out.printf('return err;')
            out.printf('}')
            out.printf()
            out.printf('// call box\'s init')
            out.printf('err = __box_%(box)s_postinit('
                '__box_%(box)s_importjumptable);')
            out.printf('if (err) {')
            with out.indent():
                out.printf('return err;')
            out.printf('}')
            out.printf()
            out.printf('__box_%(box)s_initialized = true;')
            out.printf('return 0;')
        out.printf('}')

        out = output.decls.append()
        out.printf('int __box_%(box)s_clobber(void) {')
        with out.indent():
            out.printf('__box_%(box)s_initialized = false;')
            out.printf('return 0;')
        out.printf('}')

    def build_parent_ld(self, output, parent, box):
        super().build_parent_ld(output, parent, box)

        if not output.no_sections:
            out = output.sections.append(
                box_memory=self._jumptable.memory.name,
                section='.box.%(box)s.%(box_memory)s',
                memory='box_%(box)s_%(box_memory)s')
            out.printf('__box_%(box)s_jumptable = __%(memory)s_start;')

    def build_c(self, output, box):
        super().build_c(output, box)

        out = output.decls.append()
        out.printf('//// awsm glue ////')

        output.decls.append(BOUNDS_CHECKS[self._bounds_check])
        output.decls.append(COMMON)

        out = output.decls.append()
        out.printf('//// jumptable implementation ////')
        out.printf('const uint32_t *__box_importjumptable;')

        out = output.decls.append()
        out.printf('int __box_init(const uint32_t *importjumptable) {')
        with out.indent():
            if self.data_init_hook.link:
                out.printf('// data inited by %(hook)s',
                    hook=self.data_init_hook.link.export.source)
                out.printf()
            else:
                out.printf('// load data')
                out.printf('extern uint32_t __data_init_start;')
                out.printf('extern uint32_t __data_start;')
                out.printf('extern uint32_t __data_end;')
                out.printf('const uint32_t *s = &__data_init_start;')
                out.printf('for (uint32_t *d = &__data_start; '
                    'd < &__data_end; d++) {')
                with out.indent():
                    out.printf('*d = *s++;')
                out.printf('}')
                out.printf()
            if self.bss_init_hook.link:
                out.printf('// bss inited by %(hook)s',
                    hook=self.bss_init_hook.link.export.source)
                out.printf()
            else:
                out.printf('// zero bss')
                out.printf('extern uint32_t __bss_start;')
                out.printf('extern uint32_t __bss_end;')
                out.printf('for (uint32_t *d = &__bss_start; '
                    'd < &__bss_end; d++) {')
                with out.indent():
                    out.printf('*d = 0;')
                out.printf('}')
                out.printf()
            out.printf('// set import jumptable')
            out.printf('__box_importjumptable = importjumptable;')
            out.printf()
            out.printf('// init libc')
            out.printf('extern void __libc_init_array(void);')
            out.printf('__libc_init_array();')
            out.printf()
            out.printf('// populate wasm state')
            out.printf('populate_table();')
            out.printf('populate_globals();')
            out.printf('populate_memory();')
            out.printf('wasmf___wasm_call_ctors();')
            out.printf()
            out.printf('return 0;')
        out.printf('}')

        output.decls.append('//// imports ////')
        for i, import_ in enumerate(self._imports(box)):
            out = output.decls.append(
                fn=self.repr_wasmf(import_, name='env_%(alias)s'),
                fnptr=output.repr_fnptr(import_, ''),
                alias=import_.alias,
                i=i)
            out.printf('%(fn)s {')
            with out.indent():
                out.printf('%(return_)s((%(fnptr)s)\n'
                    '        __box_importjumptable[%(i)d])(%(args)s);',
                    return_='return ' if import_.rets else '',
                    args=', '.join(
                        'to_ptr(%s)' % name if arg.isptr() else name
                        for arg, name in import_.zippedargsandbounds()))
                if import_.isnoreturn():
                    # kinda wish we could apply noreturn to C types...
                    out.printf('__builtin_unreachable();')
            out.printf('}')

        output.decls.append('//// exports ////')
        for export, _ in self._exports(box):
            out = output.decls.append(
                '%(wasmf)s;',
                wasmf=self.repr_wasmf(export,
                    name='wasmf_%(alias)s', attrs=['extern']),
                alias=export.alias)
        for export, needswrapper in  self._exports(box):
            if not needswrapper:
                continue
            out = output.decls.append(
                fn=output.repr_fn(
                    export.postbound(),
                    name='export_%(alias)s'),
                alias=export.alias)
            out.printf('%(fn)s {')
            with out.indent():
                out.printf('%(return_)swasmf_%(alias)s(%(args)s);',
                    return_='return ' if import_.rets else '',
                    args=', '.join(
                        'from_ptr(%s)' % name if arg.isptr() else name
                        for arg, name in export.zippedargsandbounds()))
            out.printf('}')

        out = output.decls.append(doc='box-side jumptable')
        out.printf('__attribute__((used, section(".jumptable")))')
        out.printf('const uint32_t __box_exportjumptable[] = {')
        with out.pushindent():
            for i, (export, needswrapper) in enumerate(self._exports(box)):
                out.printf('(uint32_t)%(prefix)s%(alias)s,',
                    prefix='export_'
                        if needswrapper else
                        'wasmf_'
                        if export.alias != '__box_init' else
                        '',
                    alias=export.alias)
                if i == 0:
                    # stack operations follow init
                    out.printf('(uint32_t)__box_push,')
                    out.printf('(uint32_t)__box_pop,')
        out.printf('};')

    def build_ld(self, output, box):
        out = output.decls.append()
        out.printf('%(symbol)-16s = DEFINED(%(symbol)s) '
            '? %(symbol)s : %(value)#010x;',
            symbol='__memory_min',
            value=self._memory.size)
        out.printf('%(symbol)-16s = DEFINED(%(symbol)s) '
            '? %(symbol)s : %(value)#010x;',
            symbol='__table_min',
            value=self._table.size)

        if not output.no_sections:
            out = output.sections.append(
                section='.jumptable',
                memory=self._jumptable.memory.name)
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__jumptable_start = .;')
            out.printf('%(section)s . : {')
            with out.pushindent():
                out.printf('__jumptable = .;')
                out.printf('KEEP(*(.jumptable))')
            out.printf('} > %(MEMORY)s')
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__jumptable_end = .;')

            out = output.sections.append(
                section='.memory',
                memory=self._memory.memory.name)
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__memory_start = .;')
            out.printf('%(section)s . (NOLOAD) : {')
            with out.pushindent():
                out.printf('__memory = .;')
                out.printf('*(.memory)')
            out.printf('} > %(MEMORY)s')
            out.printf('. += __memory_min;')
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__memory_end = .;')

            out = output.sections.append(
                section='.table',
                memory=self._table.memory.name)
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__table_start = .;')
            out.printf('%(section)s . (NOLOAD) : {')
            with out.pushindent():
                out.printf('__table = .;')
                out.printf('*(.table)')
            out.printf('} > %(MEMORY)s')
            out.printf('. += __table_min;')
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__table_end = .;')

        super().build_ld(output, box)

    def build_mk(self, output, box):
        assert not output.no_awsm, ("The runtime `%s` requires the aWsm "
            "compiler, please provide --output.mk.awsm." % self.__argname__)
        assert not output.no_llvm, ("The runtime `%s` requires an LLVM "
            "compiler, please provide --output.mk.llvm_cc=clang."
            % self.__argname__)
        assert not output.no_wasm, ("The runtime `%s` requires a WebAssembly "
            "compiler, please provide either --output.mk.wasi_sdk or "
            "--output.mk.wasm_cc." % self.__argname__)

        # target rule
        output.decls.insert(0, '%(name)-16s ?= %(target)s',
            name='TARGET', target=output.get('target', '%(box)s.elf'))

        out = output.rules.append(doc='target rule')
        out.printf('$(TARGET): $(TARGET:.elf=.awsm.o) $(LDSCRIPT)')
        with out.indent():
            out.printf('$(CC) $< $(filter-out -flto,$(LDFLAGS)) -o $@')

        out = output.rules.append()
        out.printf('$(TARGET:.elf=.awsm.o): $(TARGET:.elf=.awsm.bc)')
        with out.indent():
            out.printf('$(LLVMCC) -c $< '
                '$(filter-out -flto -I%%,$(LLVMCFLAGS)) -o $@')

        out = output.rules.append()
        out.printf('$(TARGET:.elf=.awsm.bc): $(TARGET:.elf=.bc) $(LLVMOBJ)')
        with out.indent():
            out.printf('$(LLVMLINK) $^ -o $@')
            out.printf('$(LLVMOPT) $(LLVMOPTFLAGS) $@ -o $@')

        out = output.rules.append()
        out.printf('$(TARGET:.elf=.bc): $(TARGET:.elf=.wasm)')
        with out.indent():
            out.printf('$(AWSM) $(AWSMFLAGS) $< -o $@')

        out = output.rules.append()
        out.printf('$(TARGET:.elf=.wasm): $(WASMOBJ) $(WASMBOXES)')
        with out.indent():
            out.printf('$(WASMCC) $(WASMOBJ) $(WASMBOXES) $(WASMLDFLAGS) -o $@')

        super().build_mk(output, box)

        # decls for wasm
        out = output.decls.append()
        out.printf('### wasm stack configuration ###')
        out.printf('override WASMLDFLAGS += '
            '-Wl,-z,stack-size=%(stack_size)d',
            stack_size=box.stack.size)

