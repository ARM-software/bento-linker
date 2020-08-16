
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

C_COMMON = """
__attribute__((unused))
static int __box_wasm3_toerr(M3Result res) {
    // note we can't use switch/case here because these are pointers
    if      (res == m3Err_none)                             return 0;
    // general errors
    else if (res == m3Err_typeListOverflow)                 return -ENOMEM;
    else if (res == m3Err_mallocFailed)                     return -ENOMEM;
    // parse errors
    else if (res == m3Err_incompatibleWasmVersion)          return -ENOEXEC;
    else if (res == m3Err_wasmMalformed)                    return -ENOEXEC;
    else if (res == m3Err_misorderedWasmSection)            return -ENOEXEC;
    else if (res == m3Err_wasmUnderrun)                     return -ENOEXEC;
    else if (res == m3Err_wasmOverrun)                      return -ENOEXEC;
    else if (res == m3Err_wasmMissingInitExpr)              return -ENOEXEC;
    else if (res == m3Err_lebOverflow)                      return -ENOEXEC;
    else if (res == m3Err_missingUTF8)                      return -ENOEXEC;
    else if (res == m3Err_wasmSectionUnderrun)              return -ENOEXEC;
    else if (res == m3Err_wasmSectionOverrun)               return -ENOEXEC;
    else if (res == m3Err_invalidTypeId)                    return -ENOEXEC;
    else if (res == m3Err_tooManyMemorySections)            return -ENOEXEC;
    // link errors
    else if (res == m3Err_moduleAlreadyLinked)              return -ENOEXEC;
    else if (res == m3Err_functionLookupFailed)             return -ENOEXEC;
    else if (res == m3Err_functionImportMissing)            return -ENOEXEC;
    else if (res == m3Err_malformedFunctionSignature)       return -ENOEXEC;
    else if (res == m3Err_funcSignatureMissingReturnType)   return -ENOEXEC;
    // compilation errors
    else if (res == m3Err_noCompiler)                       return -ENOEXEC;
    else if (res == m3Err_unknownOpcode)                    return -ENOEXEC;
    else if (res == m3Err_functionStackOverflow)            return -EOVERFLOW;
    else if (res == m3Err_functionStackUnderrun)            return -ENOEXEC;
    else if (res == m3Err_mallocFailedCodePage)             return -ENOMEM;
    else if (res == m3Err_settingImmutableGlobal)           return -ENOEXEC;
    else if (res == m3Err_optimizerFailed)                  return -ENOEXEC;
    // runtime errors
    else if (res == m3Err_missingCompiledCode)              return -ENOEXEC;
    else if (res == m3Err_wasmMemoryOverflow)               return -ENOEXEC;
    else if (res == m3Err_globalMemoryNotAllocated)         return -ENOEXEC;
    else if (res == m3Err_globaIndexOutOfBounds)            return -ENOEXEC;
    else if (res == m3Err_argumentCountMismatch)            return -ENOEXEC;
    // traps
    else if (res == m3Err_trapOutOfBoundsMemoryAccess)      return -EFAULT;
    else if (res == m3Err_trapDivisionByZero)               return -EDOM;
    else if (res == m3Err_trapIntegerOverflow)              return -ERANGE;
    else if (res == m3Err_trapIntegerConversion)            return -ERANGE;
    else if (res == m3Err_trapIndirectCallTypeMismatch)     return -ENOEXEC;
    else if (res == m3Err_trapTableIndexOutOfRange)         return -EFAULT;
    else if (res == m3Err_trapTableElementIsNull)           return -EFAULT;
    else if (res == m3Err_trapExit)                         return -ECANCELED;
    else if (res == m3Err_trapAbort)                        return -ECANCELED;
    else if (res == m3Err_trapUnreachable)                  return -EFAULT;
    else if (res == m3Err_trapStackOverflow)                return -EOVERFLOW;
    // fallback to general error?
    else                                                    return -EGENERAL;
}

__attribute__((unused))
static uint32_t __box_wasm3_fromptr(IM3Runtime runtime, const void *ptr) {
    return (uint32_t)((const uint8_t*)ptr
        - m3MemData(runtime->memory.mallocated));
}

__attribute__((unused))
static void *__box_wasm3_toptr(IM3Runtime runtime, uint32_t ptr) {
    return m3MemData(runtime->memory.mallocated) + ptr;
}
"""

ABORT_HOOK = """
m3ApiRawFunction(__box_%(box)s_import___box_%(box)s_abort) {
    m3ApiGetArg(int, err);
    __box_%(box)s_runtime->exit_code = err;
    m3ApiTrap(m3Err_trapExit);
}
"""

@runtimes.runtime
class Wasm3Runtime(
        ErrorGlue,
        WriteGlue,
        AbortGlue,
        HeapGlue,
        runtimes.Runtime):
    """
    A bento-box runtime using wasm3, a wasm interpreter
    """
    __argname__ = "wasm3"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser, **kwargs):
        pass
#        parser.add_nestedparser('--jumptable', Section)
#        parser.add_argument('--no_longjmp', type=bool,
#            help="Do not use longjmp for error recovery. longjmp adds a small "
#                "cost to every box entry point. --no_longjmp disables longjmp "
#                "and forces any unhandled aborts to halt. Note this has no "
#                "if an explicit __box_<box>_abort hook is provided.")

    def __init__(self):
        super().__init__()
        #self._jumptable = Section('jumptable', **jumptable.__dict__)
        #self._no_longjmp = no_longjmp or False

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
        #self._jumptable.alloc(box, 'rp')
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

    @staticmethod
    def _repr_argstringarg(arg):
        if arg.isptr():
            return '*'
        elif arg.prim() == 'f64':
            return 'F'
        elif arg.prim() == 'f32':
            return 'f'
        elif arg.primwidth() == 64:
            return 'I'
        else:
            return 'i'

    @staticmethod
    def _repr_argstring(fn):
        return ''.join(it.chain([
            Wasm3Runtime._repr_argstringarg(fn.rets[0]) if fn.rets else 'v',
            '(',
            ], (Wasm3Runtime._repr_argstringarg(arg) for arg in fn.args), [
            ')']))

    def _parentimports(self, parent, box):
        """
        Get imports that need linking.
        Yields import, needsinit.
        """
        # imports that need linking
        for import_ in parent.imports:
            if import_.link and import_.link.export.box == box:
                yield import_.postbound()

    def _parentexports(self, parent, box):
        """
        Get exports that need linking
        Yields export, needswrapper.
        """
        # implicit exports
        yield Export(
            '__box_abort',
            'fn(err) -> noreturn',
            alias='__box_%s_abort' % box.name,
            source=self.__argname__)
        yield Export(
            '__box_write',
            'fn(i32, const u8*, usize) -> errsize',
            alias='__box_%s_write' % box.name,
            source=self.__argname__)
        yield Export(
            '__box_flush',
            'fn(i32) -> err',
            alias='__box_%s_flush' % box.name,
            source=self.__argname__)

        # exports that need linking
        for export in parent.exports:
            if any(link.import_.box == box for link in export.links):
                yield export.prebound()

#    def _imports(self, box):
#        """
#        Get imports that need linking.
#        Yields import.
#        """
#        # implicit imports
#        yield Import(
#            '__box_abort',
#            'fn(err) -> noreturn',
#            source=self.__argname__)
#        yield Import(
#            '__box_write',
#            'fn(i32, const u8[size], usize size) -> errsize',
#            source=self.__argname__)
#        yield Export(
#            '__box_flush',
#            'fn(i32) -> err',
#            source=self.__argname__)
#
#        # imports that need linking
#        for import_ in box.imports:
#            if import_.link and import_.link.export.box != box:
#                yield import_.postbound()
#
#    def _exports(self, box):
#        """
#        Get exports that need linking.
#        Yields export, needswrapper.
#        """
#        # implicit exports
#        yield Export(
#            '__box_init', 'fn() -> err32',
#            source=self.__argname__), False
#
#        # exports that need linking
#        for export in box.exports:
#            if export.scope != box:
#                yield export.prebound(), len(export.boundargs) > 0

    def build_mk(self, output, box):
        # TODO error on needs wasmcc?
        assert not output.no_wasm, ("The runtime `%s` requires a WebAssembly "
            "compiler, please provide either --output.mk.wasi_sdk or "
            "--output.mk.wasm_cc" % self.__argname__)

        # target rule
        output.decls.insert(0, '%(name)-16s ?= %(target)s',
            name='TARGET', target=output.get('target', '%(box)s.wasm'))

        out = output.rules.append(doc='target rule')
        out.printf('$(TARGET): $(WASMOBJ) $(WASMBOXES) $(WASMARCHIVES)')
        with out.indent():
            out.printf('$(WASMCC) $(WASMOBJ) $(WASMBOXES) $(WASMLDFLAGS) -o $@')

        out = output.rules.append()
        out.printf('%%.elf: %%.wasm.prefixed')
        with out.indent():
            out.writef('$(strip $(OBJCOPY) $< $@')
            with out.indent():
                out.writef(' \\\n-I binary')
                out.writef(' \\\n-O elf32-littlearm')
                out.writef(' \\\n-B arm')
                out.writef(' \\\n--rename-section .data=.text,'
                    'contents,alloc,load,readonly,data')
                out.printf(')')

        super().build_mk(output, box)

    def build_h(self, output, box):
        super().build_h(output, box)

#        # TODO move to C?
#        for i, export in enumerate(
#                export.prebound() for export in box.exports
#                if export.source == box):
#            if i == 0:
#                output.decls.append('//// box export redeclared with '
#                    'correct linkage ////')
#            output.decls.append('%(fn)s;',
#                fn=output.repr_fn(export,
#                    attrs=['__attribute__((used))', 'extern']),
#                doc=export.doc)

    def build_parent_c_prologue(self, output, parent):
        super().build_parent_c_prologue(output, parent)
        output.decls.append(C_COMMON)

    def build_parent_c(self, output, parent, box):
        super().build_parent_c(output, parent, box)

        output.includes.append('<wasm3.h>')
        output.includes.append('<m3_api_defs.h>')
        output.includes.append('<m3_env.h>')

        out = output.decls.append()
        out.printf('//// %(box)s state ////')
        out.printf('bool __box_%(box)s_initialized = false;')
        out.printf('IM3Environment __box_%(box)s_environment;')
        out.printf('IM3Runtime __box_%(box)s_runtime;')
        out.printf('IM3Module __box_%(box)s_module;')

        # redirect hooks if necessary
        if not self._abort_hook.link:
            output.decls.append(ABORT_HOOK)

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

        # box imports, wasm3 makes this easy
        output.decls.append('//// %(box)s imports ////')
        for export in self._parentexports(parent, box):
            if export.name == '__box_abort' and not self._abort_hook.link:
                continue
            out = output.decls.append(
                name='__box_%(box)s_import_%(alias)s',
                alias=export.alias)
            out.printf('m3ApiRawFunction(%(name)s) {')
            with out.indent():
                if export.rets:
                    out.printf('m3ApiReturnType(%(ret)s);',
                        ret=output.repr_arg(export.rets[0]))
                for arg, name in export.zippedargs():
                    if arg.isptr():
                        out.printf('m3ApiGetArgMem(%(arg)s, %(name)s);',
                            arg=output.repr_arg(arg),
                            name=name)
                    else:
                        out.printf('m3ApiGetArg(%(arg)s, %(name)s);',
                            arg=output.repr_arg(arg),
                            name=name)
                out.printf('%(rets)s%(alias)s(%(args)s);',
                    args=', '.join(map(str, export.argnamesandbounds())),
                    rets='%s = ' % output.repr_arg(
                            export.rets[0],
                            name=export.retname())
                        if export.rets else '')
                if export.rets:
                    out.printf('m3ApiReturn(%(name)s);',
                        name=export.retname())
                elif not export.isnoreturn():
                    out.printf('m3ApiSuccess();')
            out.printf('}')


        # box exports, wasm3 doesn't have a great link layer here so
        # this is a bit hacky
        output.decls.append('//// %(box)s exports ////')
        for import_ in self._parentimports(parent, box):
            out = output.decls.append(
                fn=output.repr_fn(import_),
                # TODO handle aliases wasm side?
                linkname=import_.link.export.name,
                linkargs=len(import_.preboundargs))
            out.printf('%(fn)s {')
            with out.indent():
                # inject lazy-init?
                if box.init == 'lazy':
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
                # TODO uniquify?
                out.printf('M3Result _res;')
                out.printf('IM3Function _f;')
                out.printf('_res = m3_FindFunction(&_f,\n'
                    '        __box_%(box)s_runtime,\n'
                    '        "%(linkname)s");')
                if import_.isfalible():
                    out.printf('if (_res || !_f->compiled) '
                        'return -ENOEXEC;')
                else:
                    out.printf('assert(!_res && _f->compiled);')
                out.printf('IM3FuncType _type = _f->funcType;')
                if import_.isfalible():
                    out.printf('if (_type->numArgs != %(linkargs)d) '
                        'return -ENOEXEC;')
                else:
                    out.printf('assert(_type->numArgs == %(linkargs)d);')
                out.printf('uint64_t *stack = __box_%(box)s_runtime->stack;')
                for i, (arg, name) in enumerate(import_.zippedargsandbounds()):
                    if arg.isptr():
                        out.printf('*(uint32_t*)&stack[%(i)d] = '
                            '__box_wasm3_fromptr(%(name)s);',
                            name=name,
                            i=i)
                    else:
                        out.printf('*(%(arg)s*)&stack[%(i)d] = %(name)s;',
                            arg=output.repr_arg(arg),
                            name=name,
                            i=i)
                out.printf('m3StackCheckInit();')
                out.printf('_res = (M3Result)Call(\n'
                    '        _f->compiled,\n'
                    '        (m3stack_t)stack,\n'
                    '        __box_%(box)s_runtime->memory.mallocated,\n'
                    '        d_m3OpDefaultArgs);')
                if import_.isfalible():
                    out.printf('if (_res) {')
                    with out.indent():
                        out.printf('if (_res == m3Err_trapExit) {')
                        with out.indent():
                            out.printf('return __box_%(box)s_runtime'
                                '->exit_code;')
                        out.printf('}')
                        out.printf('return __box_wasm3_toerr(_res);')
                    out.printf('}')
                else:
                    out.printf('assert(!_res);')
                for ret in import_.rets:
                    if ret.isptr():
                        out.printf('return __box_wasm3_toptr('
                            '*(uint32_t*)&stack[0]);')
                    else:
                        out.printf('return *(%(ret)s*)&stack[0];',
                            ret=output.repr_arg(ret))
                if import_.isnoreturn():
                    # kinda wish we could apply noreturn to C types...
                    out.printf('__builtin_unreachable();')
            out.printf('}')

        # init
        output.decls.append('//// %(box)s init ////')
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
            # initialize runtime
            out.printf('// initialized wasm3 runtime')
            out.printf('M3Result res;')
            out.printf('__box_%(box)s_environment = m3_NewEnvironment();')
            out.printf('if (!__box_%(box)s_environment) return -ENOMEM;')
            out.printf('__box_%(box)s_runtime = m3_NewRuntime(\n'
                '        __box_%(box)s_environment,\n'
                '        %(stack)d,\n'
                '        NULL);',
                stack=box.stack.size)
            # TODO use this pointer for initialized state?
            out.printf('if (!__box_%(box)s_runtime) return -ENOMEM;')
            out.printf('extern uint32_t __box_%(box)s_image;')
            out.printf('res = m3_ParseModule(\n'
                '        __box_%(box)s_environment,\n'
                '        &__box_%(box)s_module,\n'
                '        (uint8_t*)(&__box_%(box)s_image + 1),\n'
                '        __box_%(box)s_image);')
            out.printf('if (res) return __box_wasm3_toerr(res);')
            out.printf()
            out.printf('res = m3_LoadModule(__box_%(box)s_runtime, '
                '__box_%(box)s_module);')
            out.printf('if (res) return __box_wasm3_toerr(res);')
            out.printf()
            if list(self._parentexports(parent, box)):
                # link imports
                out.printf('// link imports')
                for export in self._parentexports(parent, box):
                    out.printf('res = m3_LinkRawFunction(\n'
                        '        __box_%(box)s_module,\n'
                        '        "*",\n'
                        '        "%(name)s",\n'
                        '        "%(argstring)s",\n'
                        '        %(link)s);',
                        link='__box_%(box)s_import_%(alias)s',
                        name=export.name,
                        alias=export.alias,
                        argstring=self._repr_argstring(export))
                    out.printf('if (res && '
                        'res != m3Err_functionLookupFailed) {')
                    with out.indent():
                        out.printf('return __box_wasm3_toerr(res);')
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
        


#        out = output.decls.append()
#        out.printf('//// %(box)s state ////')
#        out.printf('bool __box_%(box)s_initialized = false;')
##        if not self._abort_hook.link and not self._no_longjmp:
##            out.printf('jmp_buf *__box_%(box)s_jmpbuf = NULL;')
#        if box.stack.size > 0:
#            out.printf('uint8_t *__box_%(box)s_datasp = NULL;')
#        out.printf('extern uint32_t __box_%(box)s_jumptable[];')
#        out.printf('#define __box_%(box)s_exportjumptable '
#            '__box_%(box)s_jumptable')
#
#        output.decls.append('//// %(box)s exports ////')
#
#        for i, (import_, needsinit) in enumerate(
#                self._parentimports(parent, box)):
#            out = output.decls.append(
#                fn=output.repr_fn(import_),
#                fnptr=output.repr_fnptr(import_.prebound(), ''),
#                i=i+1 if box.stack.size > 0 else i)
#            out.printf('%(fn)s {')
#            with out.indent():
#                # inject lazy-init?
#                if needsinit:
#                    out.printf('if (!__box_%(box)s_initialized) {')
#                    with out.indent():
#                        out.printf('int err = __box_%(box)s_init();')
#                        out.printf('if (err) {')
#                        with out.indent():
#                            if import_.isfalible():
#                                out.printf('return err;')
#                            else:
#                                out.printf('__box_abort(err);')
#                        out.printf('}')
#                    out.printf('}')
#                    out.printf()
#                # use longjmp?
##                if (import_.isfalible() and
##                        not self._abort_hook.link and
##                        not self._no_longjmp):
##                    with out.pushattrs(
##                            pjmpbuf=import_.uniquename('pjmpbuf'),
##                            jmpbuf=import_.uniquename('jmpbuf'),
##                            err=import_.uniquename('err')):
##                        out.printf('jmp_buf *%(pjmpbuf)s = '
##                            '__box_%(box)s_jmpbuf;')
##                        out.printf('jmp_buf %(jmpbuf)s;')
##                        out.printf('__box_%(box)s_jmpbuf = &%(jmpbuf)s;')
##                        out.printf('int %(err)s = setjmp(%(jmpbuf)s);')
##                        out.printf('if (%(err)s) {')
##                        with out.indent():
##                            out.printf('__box_%(box)s_jmpbuf = %(pjmpbuf)s;')
##                            out.printf('return %(err)s;')
##                        out.printf('}')
#                # jump to jumptable entry
##                out.printf('%(return_)s((%(fnptr)s)\n'
##                    '        __box_%(box)s_exportjumptable[%(i)d])(%(args)s);',
##                    return_=('return ' if import_.rets else '')
##                        if not (import_.isfalible() and
##                            not self._abort_hook.link and
##                            not self._no_longjmp) else
##                        ('%s = ' % output.repr_arg(import_.rets[0],
##                                import_.retname())
##                            if import_.rets else ''),
##                    args=', '.join(map(str, import_.argnamesandbounds())))
#                if import_.isnoreturn():
#                    # kinda wish we could apply noreturn to C types...
#                    out.printf('__builtin_unreachable();')
#                # use longjmp?
#                if (import_.isfalible() and
#                        not self._abort_hook.link and
#                        not self._no_longjmp):
#                    with out.pushattrs(
#                            pjmpbuf=import_.uniquename('pjmpbuf')):
#                        out.printf('__box_%(box)s_jmpbuf = %(pjmpbuf)s;')
#                        if import_.rets:
#                            out.printf('return %(ret)s;',
#                                ret=import_.retname())
#            out.printf('}')
#            
#        output.decls.append('//// %(box)s imports ////')
#
#        # redirect hooks if necessary
#        if not self._abort_hook.link:
#            if not self._no_longjmp:
#                # use longjmp to recover from explicit aborts
#                output.includes.append('<setjmp.h>')
#                out = output.decls.append(
#                    fn=output.repr_fn(self._abort_hook,
#                        self._abort_hook.name))
#                out.printf('%(fn)s {')
#                with out.indent():
#                    out.printf('__box_%(box)s_initialized = false;')
#                    out.printf('if (__box_%(box)s_jmpbuf) {')
#                    with out.indent():
#                        out.printf('longjmp(*__box_%(box)s_jmpbuf, err);')
#                    out.printf('} else {')
#                    with out.indent():
#                        out.printf('__box_abort(err);')
#                    out.printf('}')
#                out.printf('}')
#            else:
#                # just redirect to parent's __box_abort
#                out = output.decls.append(
#                    abort_hook=self._abort_hook.name,
#                    doc='redirect %(abort_hook)s -> __box_abort')
#                out.printf('#define %(abort_hook)s __box_abort')
#
#        if not self._write_hook.link:
#            out = output.decls.append(
#                write_hook=self._write_hook.name,
#                doc='redirect %(write_hook)s -> __box_write')
#            out.printf('#define %(write_hook)s __box_write')
#
#        if not self._flush_hook.link:
#            out = output.decls.append(
#                flush_hook=self._flush_hook.name,
#                doc='redirect %(flush_hook)s -> __box_flush')
#            out.printf('#define %(flush_hook)s __box_flush')
#
#        # wrappers?
#        for export in (export
#                for export, needswrapper in self._parentexports(parent, box)
#                if needswrapper):
#            out = output.decls.append(
#                fn=output.repr_fn(
#                    export.postbound(),
#                    name='__box_%(box)s_export_%(alias)s'),
#                alias=export.alias)
#            out.printf('%(fn)s {')
#            with out.indent():
#                out.printf('%(return_)s%(alias)s(%(args)s);',
#                    return_='return ' if import_.rets else '',
#                    args=', '.join(map(str, export.argnamesandbounds())))
#            out.printf('}')
#
#        # import jumptable
#        out = output.decls.append()
#        out.printf('const uint32_t __box_%(box)s_importjumptable[] = {')
#        with out.indent():
#            for export, needswrapper in self._parentexports(parent, box):
#                out.printf('(uint32_t)%(prefix)s%(alias)s,',
#                    prefix='__box_%(box)s_export_' if needswrapper else '',
#                    alias=export.alias)
#        out.printf('};')
#
#        # init
#        output.decls.append('//// %(box)s init ////')
#        out = output.decls.append()
#        out.printf('int __box_%(box)s_init(void) {')
#        with out.indent():
#            out.printf('int err;')
#            if box.roommates:
#                out.printf('// bring down any overlapping boxes')
#            for i, roommate in enumerate(box.roommates):
#                with out.pushattrs(roommate=roommate.name):
#                    out.printf('extern int __box_%(roommate)s_clobber(void);')
#                    out.printf('err = __box_%(roommate)s_clobber();')
#                    out.printf('if (err) {')
#                    with out.indent():
#                        out.printf('return err;')
#                    out.printf('}')
#                    out.printf()
#            if box.stack.size > 0:
#                out.printf('// prepare data stack')
#                out.printf('__box_%(box)s_datasp = '
#                    '(void*)__box_%(box)s_exportjumptable[0];')
#                out.printf()
#            out.printf('// load the box if unloaded')
#            out.printf('err = __box_%(box)s_load();')
#            out.printf('if (err) {')
#            with out.indent():
#                out.printf('return err;')
#            out.printf('}')
#            out.printf()
#            out.printf('// call box\'s init')
#            out.printf('err = __box_%(box)s_postinit('
#                '__box_%(box)s_importjumptable);')
#            out.printf('if (err) {')
#            with out.indent():
#                out.printf('return err;')
#            out.printf('}')
#            out.printf()
#            out.printf('__box_%(box)s_initialized = true;')
#            out.printf('return 0;')
#        out.printf('}')
#
#        out = output.decls.append()
#        out.printf('int __box_%(box)s_clobber(void) {')
#        with out.indent():
#            out.printf('__box_%(box)s_initialized = false;')
#            out.printf('return 0;')
#        out.printf('}')
#
#        # stack manipulation
#        output.includes.append('<assert.h>')
#        out = output.decls.append(
#            memory=box.stack.memory.name)
#        out.printf('void *__box_%(box)s_push(size_t size) {')
#        with out.indent():
#            if box.stack.size > 0:
#                out.printf('size = ((size+3)/4)*4;')
#                out.printf('extern uint8_t __box_%(box)s_%(memory)s_start;')
#                out.printf('if (__box_%(box)s_datasp - size '
#                        '< &__box_%(box)s_%(memory)s_start) {')
#                with out.indent():
#                    out.printf('return NULL;')
#                out.printf('}')
#                out.printf()
#                out.printf('__box_%(box)s_datasp -= size;')
#                out.printf('return __box_%(box)s_datasp;')
#            else:
#                out.printf('return NULL;')
#        out.printf('}')
#
#        out = output.decls.append(
#            memory=box.stack.memory.name)
#        out.printf('void __box_%(box)s_pop(size_t size) {')
#        with out.indent():
#            if box.stack.size > 0:
#                out.printf('size = ((size+3)/4)*4;')
#                out.printf('__attribute__((unused))')
#                out.printf('extern uint8_t __box_%(box)s_%(memory)s_end;')
#                out.printf('assert(__box_%(box)s_datasp + size '
#                    '<= &__box_%(box)s_%(memory)s_end);')
#                out.printf('__box_%(box)s_datasp += size;')
#            else:
#                out.printf('assert(false);')
#        out.printf('}')

    def build_parent_ld(self, output, parent, box):
        super().build_parent_ld(output, parent, box)

        if not output.no_sections:
            out = output.sections.append(
                box_memory=box.text.memory.name,
                section='.box.%(box)s.%(box_memory)s',
                memory='box_%(box)s_%(box_memory)s')
            out.printf('__box_%(box)s_image = __%(memory)s_start;')

#
#        if not output.no_sections:
#            out = output.sections.append(
#                box_memory=self._jumptable.memory.name,
#                section='.box.%(box)s.%(box_memory)s',
#                memory='box_%(box)s_%(box_memory)s')
#            out.printf('__box_%(box)s_jumptable = __%(memory)s_start;')

    def build_c(self, output, box):
        super().build_c(output, box)

#        out = output.decls.append()
#        out.printf('//// jumptable implementation ////')
#        out.printf('const uint32_t *__box_importjumptable;')
#
#        out = output.decls.append()
#        out.printf('int __box_init(const uint32_t *importjumptable) {')
#        with out.indent():
#            if self.data_init_hook.link:
#                out.printf('// data inited by %(hook)s',
#                    hook=self.data_init_hook.link.export.source)
#                out.printf()
#            else:
#                out.printf('// load data')
#                out.printf('extern uint32_t __data_init_start;')
#                out.printf('extern uint32_t __data_start;')
#                out.printf('extern uint32_t __data_end;')
#                out.printf('const uint32_t *s = &__data_init_start;')
#                out.printf('for (uint32_t *d = &__data_start; '
#                    'd < &__data_end; d++) {')
#                with out.indent():
#                    out.printf('*d = *s++;')
#                out.printf('}')
#                out.printf()
#            if self.bss_init_hook.link:
#                out.printf('// bss inited by %(hook)s',
#                    hook=self.bss_init_hook.link.export.source)
#                out.printf()
#            else:
#                out.printf('// zero bss')
#                out.printf('extern uint32_t __bss_start;')
#                out.printf('extern uint32_t __bss_end;')
#                out.printf('for (uint32_t *d = &__bss_start; '
#                    'd < &__bss_end; d++) {')
#                with out.indent():
#                    out.printf('*d = 0;')
#                out.printf('}')
#                out.printf()
#            out.printf('// set import jumptable')
#            out.printf('__box_importjumptable = importjumptable;')
#            out.printf()
#            out.printf('// init libc')
#            out.printf('extern void __libc_init_array(void);')
#            out.printf('__libc_init_array();')
#            out.printf()
#            out.printf('return 0;')
#        out.printf('}')
#
#        output.decls.append('//// imports ////')
#        for i, import_ in enumerate(self._imports(box)):
#            out = output.decls.append(
#                fn=output.repr_fn(import_),
#                fnptr=output.repr_fnptr(import_, ''),
#                i=i)
#            out.printf('%(fn)s {')
#            with out.indent():
#                out.printf('%(return_)s((%(fnptr)s)\n'
#                    '        __box_importjumptable[%(i)d])(%(args)s);',
#                    return_='return ' if import_.rets else '',
#                    args=', '.join(map(str, import_.argnamesandbounds())))
#                if import_.isnoreturn():
#                    # kinda wish we could apply noreturn to C types...
#                    out.printf('__builtin_unreachable();')
#            out.printf('}')
#
#        output.decls.append('//// exports ////')
#        for export in (export
#                for export, needswrapper in self._exports(box)
#                if needswrapper):
#            out = output.decls.append(
#                fn=output.repr_fn(
#                    export.postbound(),
#                    name='__box_export_%(alias)s'),
#                alias=export.alias)
#            out.printf('%(fn)s {')
#            with out.indent():
#                out.printf('%(return_)s%(alias)s(%(args)s);',
#                    return_='return ' if import_.rets else '',
#                    args=', '.join(map(str, export.argnamesandbounds())))
#            out.printf('}')
#
#        out = output.decls.append(doc='box-side jumptable')
#        if box.stack.size > 0:
#            out.printf('extern uint8_t __stack_end;')
#        out.printf('__attribute__((used, section(".jumptable")))')
#        out.printf('const uint32_t __box_exportjumptable[] = {')
#        with out.pushindent():
#            if box.stack.size > 0:
#                out.printf('(uint32_t)&__stack_end,')
#            for export, needswrapper in self._exports(box):
#                out.printf('(uint32_t)%(prefix)s%(alias)s,',
#                    prefix='__box_export_' if needswrapper else '',
#                    alias=export.alias)
#        out.printf('};')

#    def build_ld(self, output, box):
#        if not output.no_sections:
#            out = output.sections.append(
#                section='.jumptable',
#                memory=self._jumptable.memory.name)
#            out.printf('. = ALIGN(%(align)d);')
#            out.printf('__jumptable_start = .;')
#            out.printf('%(section)s . : {')
#            with out.pushindent():
#                out.printf('__jumptable = .;')
#                out.printf('KEEP(*(.jumptable))')
#            out.printf('} > %(MEMORY)s')
#            out.printf('. = ALIGN(%(align)d);')
#            out.printf('__jumptable_end = .;')
#
#        super().build_ld(output, box)

