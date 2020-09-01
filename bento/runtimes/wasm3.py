
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
// wams3 supports sharing of the M3Environment state
IM3Environment __box_wasm3_environment;

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
"""

C_STUFF = """
__attribute__((unused))
static uint32_t __box_%(box)s_fromptr(const void *ptr) {
    return (uint32_t)((const uint8_t*)ptr
        - m3MemData(__box_%(box)s_runtime->memory.mallocated));
}

__attribute__((unused))
static void *__box_%(box)s_toptr(uint32_t ptr) {
    return m3MemData(__box_%(box)s_runtime->memory.mallocated) + ptr;
}

void *__box_%(box)s_push(size_t size) {
    // we maintain a separate stack in the wasm memory space,
    // sharing the stack space of the wasm-side libc
    uint32_t psp = __box_%(box)s_datasp;
    if (psp + size > %(data_stack)d) {
        return NULL;
    }

    __box_%(box)s_datasp = psp + size;
    return __box_%(box)s_toptr(psp);
}

void __box_%(box)s_pop(size_t size) {
    assert(__box_%(box)s_datasp - size >= 0);
    __box_%(box)s_datasp -= size;
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
    A bento-box runtime using Wasm3, a wasm interpreter
    """
    __argname__ = "wasm3"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser, **kwargs):
        parser.add_nestedparser('--interp_stack', Section,
            help="Size of Wasm3 interpreter stack in bytes. By "
                "default this is set to be the same as --stack, but "
                "note these are unrelated.")

    def __init__(self, interp_stack=None):
        super().__init__()
        self._interp_stack = (Section('interp_stack', **interp_stack.__dict__)
            if interp_stack.size is not None else
            None)

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
        if self._interp_stack is None:
            self._interp_stack = box.stack
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

    def build_mk(self, output, box):
        assert not output.no_wasm, ("The runtime `%s` requires a WebAssembly "
            "compiler, please provide either --output.mk.wasi_sdk or "
            "--output.mk.wasm_cc" % self.__argname__)

        # target rule
        output.decls.insert(0, '%(name)-16s ?= %(target)s',
            name='TARGET', target=output.get('target', '%(box)s.wasm'))

        out = output.rules.append(doc='target rule')
        out.printf('$(TARGET): $(WASMOBJ) $(WASMCRATES) $(WASMBOXES)')
        with out.indent():
            out.printf('$(WASMCC) $(WASMOBJ) $(WASMBOXES) $(WASMLDFLAGS) -o $@')

        out = output.rules.append()
        out.printf('%%.elf: %%.wasm.stripped.prefixed')
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

        # decls for wasm
        out = output.decls.append()
        out.printf('### wasm stack configuration ###')
        out.printf('override WASMLDFLAGS += '
            '-Wl,-z,stack-size=%(data_stack)d',
            data_stack=box.stack.size)
        for i, export in enumerate(
                export.prebound() for export in box.exports
                if export.source == box):
            out.printf('override WASMLDFLAGS += '
                '-Wl,--export=%(export)s',
                export=export.name)

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
        out.printf('IM3Runtime __box_%(box)s_runtime;')
        out.printf('IM3Module __box_%(box)s_module;')
        out.printf('uint32_t __box_%(box)s_datasp;')

        output.decls.append(C_STUFF,
            data_stack=box.stack.size)

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
                        ret=output.repr_arg(export.rets[0], name=''))
                for arg, name in export.zippedargs():
                    if arg.isptr():
                        out.printf('m3ApiGetArgMem(%(arg)s, %(name)s);',
                            arg=output.repr_arg(arg, name=''),
                            name=name)
                    else:
                        out.printf('m3ApiGetArg(%(arg)s, %(name)s);',
                            arg=output.repr_arg(arg, name=''),
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
                linkargs=len(import_.preboundargs),
                res=import_.uniquename('res'),
                f=import_.uniquename('f'))
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
                out.printf('M3Result %(res)s;')
                out.printf('IM3Function %(f)s;')
                out.printf('%(res)s = m3_FindFunction(&%(f)s,\n'
                    '        __box_%(box)s_runtime,\n'
                    '        "%(linkname)s");')
                out.printf('if (%(res)s || !%(f)s->compiled ||\n'
                    '        %(f)s->funcType->numArgs != %(linkargs)d) {')
                with out.indent():
                    if import_.isfalible():
                        out.printf('return -ENOEXEC;')
                    else:
                        out.printf('__box_abort(-ENOEXEC);')
                out.printf('}')
                out.printf()
                out.printf('uint64_t *stack = __box_%(box)s_runtime->stack;')
                for i, (arg, name) in enumerate(import_.zippedargsandbounds()):
                    if arg.isptr():
                        out.printf('*(uint32_t*)&stack[%(i)d] = '
                            '__box_%(box)s_fromptr(%(name)s);',
                            name=name,
                            i=i)
                    else:
                        out.printf('*(%(arg)s*)&stack[%(i)d] = %(name)s;',
                            arg=output.repr_arg(arg, name=''),
                            name=name,
                            i=i)
                out.printf('m3StackCheckInit();')
                out.printf('%(res)s = (M3Result)Call(\n'
                    '        %(f)s->compiled,\n'
                    '        (m3stack_t)stack,\n'
                    '        __box_%(box)s_runtime->memory.mallocated,\n'
                    '        d_m3OpDefaultArgs);')
                out.printf('if (%(res)s) {')
                with out.indent():
                    if import_.isfalible():
                        out.printf('if (%(res)s == m3Err_trapExit) {')
                        with out.indent():
                            out.printf('return __box_%(box)s_runtime'
                                '->exit_code;')
                        out.printf('}')
                        out.printf('return __box_wasm3_toerr(%(res)s);')
                    else:
                        out.printf('__box_abort('
                            '-__box_wasm3_toerr(%(res)s));')
                out.printf('}')
                for ret in import_.rets:
                    if ret.isptr():
                        out.printf('return __box_%(box)s_toptr('
                            '*(uint32_t*)&stack[0]);')
                    else:
                        out.printf('return *(%(ret)s*)&stack[0];',
                            ret=output.repr_arg(ret, name=''))
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
            # initialize environment
            out.printf('// initialize wasm3 environment, this only needs')
            out.printf('// to be done once')
            out.printf('if (!__box_wasm3_environment) {')
            with out.indent():
                out.printf('__box_wasm3_environment = m3_NewEnvironment();')
                out.printf('if (!__box_wasm3_environment) {')
                with out.indent():
                    out.printf('return -ENOMEM;')
                out.printf('}')
            out.printf('}')
            out.printf()
            # initialize runtime
            out.printf('// initialize wasm3 runtime')
            out.printf('__box_%(box)s_runtime = m3_NewRuntime(\n'
                '        __box_wasm3_environment,\n'
                '        %(interp_stack)d,\n'
                '        NULL);',
                interp_stack=self._interp_stack.size)
            # TODO use this pointer for initialized state?
            out.printf('if (!__box_%(box)s_runtime) {')
            with out.indent():
                out.printf('return -ENOMEM;')
            out.printf('}')
            out.printf('extern uint32_t __box_%(box)s_image;')
            out.printf('M3Result res;')
            out.printf('res = m3_ParseModule(\n'
                '        __box_wasm3_environment,\n'
                '        &__box_%(box)s_module,\n'
                '        (const uint8_t*)(&__box_%(box)s_image + 1),\n'
                '        __box_%(box)s_image);')
            out.printf('if (res) {')
            with out.indent():
                out.printf('return __box_wasm3_toerr(res);')
            out.printf('}')
            out.printf()
            out.printf('res = m3_LoadModule(__box_%(box)s_runtime, '
                '__box_%(box)s_module);')
            out.printf('if (res) {')
            with out.indent():
                out.printf('return __box_wasm3_toerr(res);')
            out.printf('}')
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
            out.printf('// setup data stack, note address 0 is NULL')
            out.printf('// so we can\'t start there!')
            out.printf('__box_%(box)s_datasp = 4;')
            out.printf()
            out.printf('__box_%(box)s_initialized = true;')
            out.printf('return 0;')
        out.printf('}')

        out = output.decls.append()
        out.printf('int __box_%(box)s_clobber(void) {')
        with out.indent():
            out.printf('if (__box_%(box)s_initialized) {')
            with out.indent():
                out.printf('m3_FreeRuntime(__box_%(box)s_runtime);')
            out.printf('}')
            out.printf('__box_%(box)s_initialized = false;')
            out.printf('return 0;')
        out.printf('}')

    def build_parent_ld(self, output, parent, box):
        super().build_parent_ld(output, parent, box)

        if not output.no_sections:
            out = output.sections.append(
                box_memory=box.text.memory.name,
                section='.box.%(box)s.%(box_memory)s',
                memory='box_%(box)s_%(box_memory)s')
            out.printf('__box_%(box)s_image = __%(memory)s_start;')


