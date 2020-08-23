
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

@runtimes.runtime
class JumptableRuntime(
        ErrorGlue,
        WriteGlue,
        AbortGlue,
        HeapGlue,
        runtimes.Runtime):
    """
    A bento-box runtime that uses a jumptable to link between different
    boxes. No security is applied.
    """
    __argname__ = "jumptable"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser, **kwargs):
        parser.add_nestedparser('--jumptable', Section)
        parser.add_argument('--no_longjmp', type=bool,
            help="Do not use longjmp for error recovery. longjmp adds a small "
                "cost to every box entry point. --no_longjmp disables longjmp "
                "and forces any unhandled aborts to halt. Note this has no "
                "affetc if an explicit __box_<box>_abort hook is provided.")

    def __init__(self, jumptable=None, no_longjmp=None):
        super().__init__()
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
        self._jumptable.alloc(box, 'rp')
        box.stack.alloc(box, 'rw')
        box.heap.alloc(box, 'rw')
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
           r'fn(const u32*) -> err32',
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
                yield export.prebound(), len(export.boundargs) > 0

    def build_mk(self, output, box):
        # target rule
        output.decls.insert(0, '%(name)-16s ?= %(target)s',
            name='TARGET', target=output.get('target', '%(box)s.elf'))

        out = output.rules.append(doc='target rule')
        out.printf('$(TARGET): $(OBJ) $(BOXES) $(LDSCRIPT)')
        with out.indent():
            out.printf('$(CC) $(OBJ) $(BOXES) $(LDFLAGS) -o $@')

        super().build_mk(output, box)

    def build_parent_c(self, output, parent, box):
        super().build_parent_c(output, parent, box)

        out = output.decls.append()
        out.printf('//// %(box)s state ////')
        out.printf('bool __box_%(box)s_initialized = false;')
        if not self._abort_hook.link and not self._no_longjmp:
            out.printf('jmp_buf *__box_%(box)s_jmpbuf = NULL;')
        if box.stack.size > 0:
            out.printf('uint8_t *__box_%(box)s_datasp = NULL;')
        out.printf('extern uint32_t __box_%(box)s_jumptable[];')
        out.printf('#define __box_%(box)s_exportjumptable '
            '__box_%(box)s_jumptable')

        output.decls.append('//// %(box)s exports ////')

        for i, (import_, needsinit) in enumerate(
                self._parentimports(parent, box)):
            out = output.decls.append(
                fn=output.repr_fn(import_),
                fnptr=output.repr_fnptr(import_.prebound(), ''),
                i=i+1 if box.stack.size > 0 else i)
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
            if box.stack.size > 0:
                out.printf('// prepare data stack')
                out.printf('__box_%(box)s_datasp = '
                    '(void*)__box_%(box)s_exportjumptable[0];')
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

        # stack manipulation
        output.includes.append('<assert.h>')
        out = output.decls.append(
            memory=box.stack.memory.name)
        out.printf('void *__box_%(box)s_push(size_t size) {')
        with out.indent():
            if box.stack.size > 0:
                out.printf('size = ((size+3)/4)*4;')
                out.printf('extern uint8_t __box_%(box)s_%(memory)s_start;')
                out.printf('if (__box_%(box)s_datasp - size '
                        '< &__box_%(box)s_%(memory)s_start) {')
                with out.indent():
                    out.printf('return NULL;')
                out.printf('}')
                out.printf()
                out.printf('__box_%(box)s_datasp -= size;')
                out.printf('return __box_%(box)s_datasp;')
            else:
                out.printf('return NULL;')
        out.printf('}')

        out = output.decls.append(
            memory=box.stack.memory.name)
        out.printf('void __box_%(box)s_pop(size_t size) {')
        with out.indent():
            if box.stack.size > 0:
                out.printf('size = ((size+3)/4)*4;')
                out.printf('__attribute__((unused))')
                out.printf('extern uint8_t __box_%(box)s_%(memory)s_end;')
                out.printf('assert(__box_%(box)s_datasp + size '
                    '<= &__box_%(box)s_%(memory)s_end);')
                out.printf('__box_%(box)s_datasp += size;')
            else:
                out.printf('assert(false);')
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
            out.printf('return 0;')
        out.printf('}')

        output.decls.append('//// imports ////')
        for i, import_ in enumerate(self._imports(box)):
            out = output.decls.append(
                fn=output.repr_fn(import_),
                fnptr=output.repr_fnptr(import_, ''),
                i=i)
            out.printf('%(fn)s {')
            with out.indent():
                out.printf('%(return_)s((%(fnptr)s)\n'
                    '        __box_importjumptable[%(i)d])(%(args)s);',
                    return_='return ' if import_.rets else '',
                    args=', '.join(map(str, import_.argnamesandbounds())))
                if import_.isnoreturn():
                    # kinda wish we could apply noreturn to C types...
                    out.printf('__builtin_unreachable();')
            out.printf('}')

        output.decls.append('//// exports ////')
        for export in (export
                for export, needswrapper in self._exports(box)
                if needswrapper):
            out = output.decls.append(
                fn=output.repr_fn(
                    export.postbound(),
                    name='__box_export_%(alias)s'),
                alias=export.alias)
            out.printf('%(fn)s {')
            with out.indent():
                out.printf('%(return_)s%(alias)s(%(args)s);',
                    return_='return ' if import_.rets else '',
                    args=', '.join(map(str, export.argnamesandbounds())))
            out.printf('}')

        out = output.decls.append(doc='box-side jumptable')
        if box.stack.size > 0:
            out.printf('extern uint8_t __stack_end;')
        out.printf('__attribute__((used, section(".jumptable")))')
        out.printf('const uint32_t __box_exportjumptable[] = {')
        with out.pushindent():
            if box.stack.size > 0:
                out.printf('(uint32_t)&__stack_end,')
            for export, needswrapper in self._exports(box):
                out.printf('(uint32_t)%(prefix)s%(alias)s,',
                    prefix='__box_export_' if needswrapper else '',
                    alias=export.alias)
        out.printf('};')

    def build_ld(self, output, box):
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

        super().build_ld(output, box)

