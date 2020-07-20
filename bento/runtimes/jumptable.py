
import itertools as it
import math
from .. import argstuff
from .. import runtimes
from ..box import Fn, Section, Region, Import, Export
from ..glue.error_glue import ErrorGlue
from ..glue.write_glue import WriteGlue
from ..glue.abort_glue import AbortGlue
from ..outputs import OutputBlob

@runtimes.runtime
class JumptableRuntime(ErrorGlue, WriteGlue, AbortGlue, runtimes.Runtime):
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
                "if an explicit __box_<box>_abort hook is provided.")

    def __init__(self, jumptable=None, no_longjmp=None):
        super().__init__()
        self._jumptable = Section('jumptable', **jumptable.__dict__)
        self._no_longjmp = no_longjmp or False

    def box_parent(self, parent, box):
        self._load_hook = parent.addimport(
            '__box_%s_load' % box.name, 'fn() -> err',
            target=parent.name, source=self.__argname__,
            doc="Called to load the box during init. Normally provided "
                "by the loader but can be overriden.")
        self._abort_hook = parent.addimport(
            '__box_%s_abort' % box.name, 'fn(err err) -> noreturn',
            target=parent.name, source=self.__argname__, weak=True,
            doc="Called when this box aborts, either due to an illegal "
                "memory access or other failure. the error code is "
                "provided as an argument.")
        self._write_hook = parent.addimport(
            '__box_%s_write' % box.name,
            'fn(i32, const u8*, usize) -> errsize',
            target=parent.name, source=self.__argname__, weak=True,
            doc="Override __box_write for this specific box.")
        super().box_parent(parent, box)

    def box(self, box):
        if box.stack.size:
            print("warning: Stack allocated in box `%s`, but not used by "
                "runtime %r" % (box.name, self.__argname__))
        super().box(box)
        self._jumptable.alloc(box, 'rp')
        # plugs
        self._abort_plug = box.addexport(
            '__box_abort', 'fn(err32) -> noreturn',
            target=box.name, source=self.__argname__, weak=True)
        self._write_plug = box.addexport(
            '__box_write', 'fn(i32, const u8*, usize) -> errsize',
            target=box.name, source=self.__argname__, weak=True)

    def _parentimports(self, parent, box):
        """ Get imports that need linking. """
        # implicit imports
        yield Import(
            '__box_init', 'fn(const u32*) -> err32',
            alias='__box_%s_postinit' % box.name,
            source=self.__argname__)

        # imports that need linking
        for import_ in parent.imports:
            if import_.link and import_.link.export.box == box:
                yield import_

    def _parentexports(self, parent, box):
        """ Get exports that need linking. """
        # implicit exports
        yield Export(
            '__box_%s_abort' % box.name,
            'fn(err) -> noreturn',
            source=self.__argname__)
        yield Export(
            '__box_%s_write' % box.name,
            'fn(i32, const u8*, usize) -> errsize',
            source=self.__argname__)

        # exports that need linking
        for export in parent.exports:
            if any(link.import_.box == box for link in export.links):
                yield export

    def _exports(self, box):
        """ Get exports that need linking. """
        # implicit exports
        yield Export(
            '__box_init', 'fn(const u32*) -> err32',
            source=self.__argname__)

        # exports that need linking
        for export in box.exports:
            if export.target != box:
                yield export

    def _imports(self, box):
        """ Get imports that need linking. """
        # implicit imports
        yield Import(
            '__box_%s_abort' % box.name,
            'fn(err) -> noreturn',
            alias='__box_abort',
            source=self.__argname__)
        yield Import(
            '__box_%s_write' % box.name,
            'fn(i32, const u8*, usize) -> errsize',
            alias='__box_write',
            source=self.__argname__)

        # imports that need linking
        for import_ in box.imports:
            if import_.link and import_.link.export.box != box:
                yield import_

    def _exports(self, box):
        """ Get exports that need linking. """
        # implicit exports
        yield Export(
            '__box_init', 'fn() -> err32',
            source=self.__argname__)

        # exports that need linking
        for export in box.exports:
            if export.target != box:
                yield export

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

        for i, import_ in enumerate(self._parentimports(parent, box)):
            out = output.decls.append(
                fn=output.repr_fn(import_),
                fnptr=output.repr_fnptr(import_, ''),
                i=i)
            out.printf('%(fn)s {')
            with out.indent():
                # inject lazy-init?
                if box.init == 'lazy' and import_.name != '__box_init':
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
                    args=', '.join(import_.argnames()))
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
                        self._abort_hook.linkname))
                out.printf('%(fn)s {')
                with out.indent():
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
                    abort_hook=self._abort_hook.linkname,
                    doc='redirect %(abort_hook)s -> __box_abort')
                out.printf('#define %(abort_hook)s __box_abort')

        if not self._write_hook.link:
            out = output.decls.append(
                write_hook=self._write_hook.linkname,
                doc='redirect %(write_hook)s -> __box_write')
            out.printf('#define %(write_hook)s __box_write')

        out = output.decls.append()
        out.printf('const uint32_t __box_%(box)s_importjumptable[] = {')
        with out.indent():
            for export in self._parentexports(parent, box):
                out.printf('(uint32_t)%(alias)s,', alias=export.alias)
        out.printf('};')

        output.decls.append('//// %(box)s init ////')
        out = output.decls.append()
        out.printf('int __box_%(box)s_clobber(void) {')
        with out.indent():
            out.printf('__box_%(box)s_initialized = false;')
            out.printf('return 0;')
        out.printf('}')

        out = output.decls.append()
        out.printf('int __box_%(box)s_init(void) {')
        with out.indent():
            out.printf('int err;')
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

    def build_parent_ld(self, output, parent, box):
        super().build_parent_ld(output, parent, box)

        if output.emit_sections:
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
                    args=', '.join(import_.argnames()))
                if import_.isnoreturn():
                    # kinda wish we could apply noreturn to C types...
                    out.printf('__builtin_unreachable();')
            out.printf('}')

        out = output.decls.append(doc='box-side jumptable')
        out.printf('__attribute__((used, section(".jumptable")))')
        out.printf('const uint32_t __box_exportjumptable[] = {')
        with out.pushindent():
            for export in self._exports(box):
                out.printf('(uint32_t)%(alias)s,', alias=export.alias)
        out.printf('};')

    def build_ld(self, output, box):
        if output.emit_sections:
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

