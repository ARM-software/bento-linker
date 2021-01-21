#
# Runtime for the wasm-micro-runtime, an interpreter targeting microcontrollers
# 
# Copyright (c) 2020, Arm Limited. All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause
#

import itertools as it
import math
from .. import argstuff
from .. import runtimes
from ..box import Fn, Section, Region, Import, Export
from ..glue.error_glue import ErrorGlue
from ..glue.write_glue import WriteGlue
from ..glue.abort_glue import AbortGlue
from ..glue.heap_glue import HeapGlue
from ..outputs import OutputBlob, HOutput

C_COMMON = """
// wamr shares runtime state, this means imports are shared which
// can cause problems
//
// TODO enforce independent imports...
bool __box_wamr_runtime_initialized = false;
"""

C_STUFF = """
void *__box_%(box)s_push(size_t size) {
    // we maintain a separate stack in the wasm memory space,
    // sharing the stack space of the wasm-side libc
    uint32_t psp = __box_%(box)s_datasp;
    if (psp + size > %(data_stack)d) {
        return NULL;
    }

    __box_%(box)s_datasp = psp + size;
    return wasm_runtime_addr_app_to_native(
            __box_%(box)s_module_inst, psp);
}

void __box_%(box)s_pop(size_t size) {
    assert(__box_%(box)s_datasp - size >= 0);
    __box_%(box)s_datasp -= size;
}

"""

ABORT_HOOK = """
void __box_%(box)s_import___box_%(box)s_abort(
        wasm_exec_env_t env, int err) {
    wasm_module_inst_t module = wasm_runtime_get_module_inst(env);
    int *perr = wasm_runtime_get_user_data(env);
    *perr = err;
    wasm_runtime_set_exception(module, "__box_abort");
}
"""


@runtimes.runtime
class WamrRuntime(
        ErrorGlue,
        WriteGlue,
        AbortGlue,
        HeapGlue,
        runtimes.Runtime):
    """
    A bento-box runtime using Wamr, a wasm interpreter
    """
    __argname__ = "wamr"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser, **kwargs):
        parser.add_nestedparser('--interp_stack', Section,
            help="Size of Wamr interpreter stack in bytes. By "
                "default this is set to be the same as --stack, but "
                "note these are unrelated.")
        parser.add_argument('--aot', type=bool,
            help="ahead-of-time compile the WebAssembly input into "
                "Wamr's .aot format. Requires --output.mk.wamrc to be "
                "provided.")

    def __init__(self, interp_stack=None, aot=None):
        super().__init__()
        self._interp_stack = (Section('interp_stack', **interp_stack.__dict__)
            if interp_stack.size is not None else
            None)
        self._aot = aot or False

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
            '(',
            ], (WamrRuntime._repr_argstringarg(arg) for arg in fn.args), [
            ')',
            WamrRuntime._repr_argstringarg(fn.rets[0]) if fn.rets else '']))

    @staticmethod
    def _repr_fn(fn, name=None, attrs=[]):
        # this is the same except with the additional wasm_exec_env_t arg
        return ''.join(it.chain(
            (attr + ('\n' if attr.startswith('__') else ' ')
                for attr in it.chain(
                    (['__attribute__((noreturn))']
                        if fn.isnoreturn() and (
                            name is None or '*' not in name) else
                        []) +
                    attrs)), [
            '%s ' % HOutput.repr_arg(fn.rets[0], '') if fn.rets else
            'void ',
            name if name is not None else fn.alias,
            '(',
            ', '.join(it.chain(
                ['wasm_exec_env_t %s' % fn.uniquename('env')],
                (HOutput.repr_arg(arg, name)
                    for arg, name in zip(fn.args, fn.argnames()))))
            if fn.args else
            'void',
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

    def build_parent_mk_epilogue(self, output, parent):
        # define that can be used to conditional compile the
        # needed parts of WAMR
        out = output.decls.append()
        out.printf('### defines for interpreter behavior ###')
        if any(not box.runtime._aot for box in parent.boxes
                if box.runtime == self):
            out.printf('override CFLAGS += -D__BOX_WAMR_INTERP=1')
        if any(box.runtime._aot for box in parent.boxes
                if box.runtime == self):
            out.printf('override CFLAGS += -D__BOX_WAMR_AOT=1')

        super().build_parent_mk_epilogue(output, parent)

    def build_mk(self, output, box):
        assert not output.no_wasm, ("The runtime `%s` requires a WebAssembly "
            "compiler, please provide either --output.mk.wasi_sdk or "
            "--output.mk.wasm_cc" % self.__argname__)
        if self._aot:
            assert not output.no_wamrc, ("The runtime `%s` requires a Wamr "
                "ahead-of-time compiler, please provide --output.mk.wamrc."
                "" % self.__argname__)

        # target rule
        if self._aot:
            output.decls.insert(0, '%(name)-16s ?= %(target)s',
                name='TARGET', target=output.get('target', '%(box)s.aot'))

            out = output.rules.append(doc='target rule')
            out.printf('$(TARGET): $(TARGET:.aot=.wasm)')
            with out.indent():
                out.printf('$(WAMRC) $(WAMRCFLAGS) -o $@ $<')

            out = output.rules.append()
            out.printf('$(TARGET:.aot=.wasm): '
                '$(WASMOBJ) $(WASMCRATES) $(WASMBOXES)')
            with out.indent():
                out.printf('$(WASMCC) '
                    '$(WASMOBJ) $(WASMBOXES) $(WASMLDFLAGS) -o $@')

            out = output.rules.append()
            out.printf('%%.elf: %%.aot.prefixed')
            with out.indent():
                out.writef('$(strip $(OBJCOPY) $< $@')
                with out.indent():
                    out.writef(' \\\n-I binary')
                    out.writef(' \\\n-O elf32-littlearm')
                    out.writef(' \\\n-B arm')
                    out.writef(' \\\n--rename-section .data=.text,'
                        'contents,alloc,load,readonly,data')
                    out.printf(')')
        else:
            output.decls.insert(0, '%(name)-16s ?= %(target)s',
                name='TARGET', target=output.get('target', '%(box)s.wasm'))

            out = output.rules.append(doc='target rule')
            out.printf('$(TARGET): $(WASMOBJ) $(WASMCRATES) $(WASMBOXES)')
            with out.indent():
                out.printf('$(WASMCC) '
                    '$(WASMOBJ) $(WASMBOXES) $(WASMLDFLAGS) -o $@')

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

        output.includes.append('wasm_export.h')
        output.decls.append(C_COMMON)

    def build_parent_c(self, output, parent, box):
        super().build_parent_c(output, parent, box)

        out = output.decls.append()
        out.printf('//// %(box)s state ////')
        out.printf('bool __box_%(box)s_initialized = false;')
        out.printf('uint32_t __box_%(box)s_datasp;')
        out.printf('wasm_module_t __box_%(box)s_module;')
        out.printf('wasm_module_inst_t __box_%(box)s_module_inst;')
        out.printf('wasm_exec_env_t __box_%(box)s_exec_env;')
        out.printf('int __box_%(box)s_err;')

        # redirect hooks if necessary
        if not self._abort_hook.link:
            out = output.decls.append(ABORT_HOOK,
                doc='default __box_abort implementation')

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

        # box imports, wamr makes this too easy
        output.decls.append('//// %(box)s imports ////')
        for export in self._parentexports(parent, box):
            if export.name == '__box_abort' and not self._abort_hook.link:
                continue
            out = output.decls.append(
                fn=self._repr_fn(export, name='__box_%(box)s_import_%(alias)s'),
                alias=export.alias)
            out.printf('%(fn)s {')
            with out.indent():
                out.printf('%(rets)s%(alias)s(%(args)s);',
                    args=', '.join(map(str, export.argnamesandbounds())),
                    rets='return ' if export.rets else '')
            out.printf('}')

        out = output.decls.append()
        out.printf('const NativeSymbol __box_%(box)s_native_symbols[] = {')
        with out.indent():
            for export in self._parentexports(parent, box):
                out.printf('{')
                with out.indent():
                    out.printf('"%(name)s",',
                        name=export.name)
                    out.printf('__box_%(box)s_import_%(alias)s,',
                        alias=export.alias)
                    out.printf('"%(argstring)s",',
                        argstring=self._repr_argstring(export))
                    out.printf('%(user_data)s,',
                        user_data='&__box_%(box)s_err'
                            if export.name == '__box_abort' and
                                not self._abort_hook.link else
                            'NULL')
                out.printf('},')
        out.printf('};')

        # box exports
        output.decls.append('//// %(box)s exports ////')
        for import_ in self._parentimports(parent, box):
            argsize = sum(arg.size() for arg in import_.preboundargs) // 4
            retsize = sum(ret.size() for ret in import_.rets) // 4
            framesize = max(argsize, retsize)
            out = output.decls.append(
                fn=output.repr_fn(import_),
                # TODO handle aliases wasm side?
                linkname=import_.link.export.name,
                argstring=self._repr_argstring(import_),
                f=import_.uniquename('f'),
                res=import_.uniquename('res'),
                frame=import_.uniquename('frame') if framesize else 'NULL',
                argsize=argsize,
                retsize=retsize,
                framesize=framesize)
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
                out.printf('wasm_function_inst_t %(f)s;')
                out.printf('%(f)s = wasm_runtime_lookup_function(\n'
                    '    __box_%(box)s_module_inst,\n',
                    '    "%(linkname)s",\n'
                    '    "%(argstring)s");')
                out.printf('if (!%(f)s) {')
                with out.indent():
                    if import_.isfalible():
                        out.printf('return -ENOEXEC;')
                    else:
                        out.printf('__box_abort(-ENOEXEC);')
                out.printf('}')
                out.printf()
                if import_.isfalible():
                    out.printf('__box_%(box)s_err = 0;')
                out.printf()
                if framesize:
                    # this needs to be uint8_t due to frustrating aliasing
                    # rules... And GCC ignores __attribute__((may_alias))?
                    out.printf('__attribute__((aligned(4)))')
                    out.printf('uint8_t frame[4*%(framesize)d];')
                    i = 0
                    for arg, value in import_.zippedargsandbounds():
                        if arg.isptr():
                            out.printf('*(int32_t*)&%(frame)s[4*%(i)d] '
                                '= wasm_runtime_addr_native_to_app(\n'
                                '    __box_%(box)s_module_inst,\n'
                                '    (void*)%(value)s);',
                                value=value,
                                i=i)
                        else:
                            out.printf('*(%(arg)s*)&%(frame)s[4*%(i)d] '
                                '= %(value)s;',
                                arg=output.repr_arg(arg, name=''),
                                value=value,
                                i=i)
                        i += arg.size() // 4
                out.printf('bool %(res)s = wasm_runtime_call_wasm(\n'
                    '    __box_%(box)s_exec_env,\n'
                    '    %(f)s,\n'
                    '    %(argsize)d,\n'
                    '    (uint32_t*)%(frame)s);')
                out.printf('if (!%(res)s) {')
                with out.indent():
                    if import_.isfalible():
                        out.printf('if (__box_%(box)s_err) {')
                        with out.indent():
                            out.printf('wasm_runtime_set_exception(\n'
                                '    __box_%(box)s_module_inst,\n'
                                '    NULL);')
                            out.printf('return __box_%(box)s_err;')
                        out.printf('}')
                        out.printf('return -EFAULT;')
                    else:
                        out.printf('__box_abort(-EFAULT);')
                out.printf('}')
                for ret in import_.rets:
                    out.printf()
                    if ret.isptr():
                        out.printf('return wasm_runtime_addr_app_to_native(\n'
                            '    __box_%(box)s_module_inst,\n'
                            '    *(int32_t*)&frame[4*0]);')
                    else:
                        out.printf('return *(%(ret)s*)&frame[4*0];',
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
            # runtime config
            out.printf('// bring up common runtime')
            out.printf('if (!__box_wamr_runtime_initialized) {')
            with out.indent():
                out.printf('bool success = wasm_runtime_init();')
                out.printf('if (!success) {')
                with out.indent():
                    out.printf('return -EGENERAL;')
                out.printf('}')
                out.printf('__box_wamr_runtime_initialized = true;')
            out.printf('}')
            out.printf()
            # hook in native functions
            # TODO isolate per box somehow?
            out.printf('if (!__box_%(box)s_module) {')
            with out.indent():
                out.printf('bool success = wasm_runtime_register_natives(\n'
                    '    "env",\n'
                    '    (NativeSymbol*)__box_%(box)s_native_symbols,\n'
                    '    sizeof(__box_%(box)s_native_symbols) / '
                            'sizeof(NativeSymbol));')
                out.printf('if (!success) {')
                with out.indent():
                    out.printf('return -EGENERAL;')
                out.printf('}')
            out.printf('}')
            out.printf()
            # wasm image parsing
            out.printf('extern uint32_t __box_%(box)s_image;')
            out.printf('__box_%(box)s_module = wasm_runtime_load(\n'
                '    (const uint8_t*)(&__box_%(box)s_image + 1),\n'
                '    __box_%(box)s_image,\n'
                '    NULL, 0);')
            out.printf('if (!__box_%(box)s_module) {')
            with out.indent():
                out.printf('return -ENOEXEC;')
            out.printf('}')
            out.printf()
            out.printf('__box_%(box)s_module_inst = wasm_runtime_instantiate(\n'
                '    __box_%(box)s_module,\n'
                '    %(interp_stack)d,\n'
                '    0,\n'
                '    NULL, 0);',
                interp_stack=self._interp_stack.size)
            out.printf('if (!__box_%(box)s_module_inst) {')
            with out.indent():
                out.printf('return -ENOEXEC;')
            out.printf('}')
            out.printf()
            out.printf('__box_%(box)s_exec_env = '
                'wasm_runtime_create_exec_env(\n'
                '    __box_%(box)s_module_inst,\n'
                '    %(interp_stack)d);',
                interp_stack=self._interp_stack.size)
            out.printf('if (!__box_%(box)s_exec_env) {')
            with out.indent():
                out.printf('return -ENOEXEC;')
            out.printf('}')
            out.printf()
            out.printf('wasm_runtime_set_user_data(\n'
                '    __box_%(box)s_exec_env,\n'
                '    &__box_%(box)s_err);')
            out.printf()
            # just a few other state things
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
                out.printf('wasm_runtime_destroy_exec_env('
                    '__box_%(box)s_exec_env);')
                out.printf('wasm_runtime_deinstantiate('
                    '__box_%(box)s_module_inst);')
                out.printf('wasm_runtime_unload('
                    '__box_%(box)s_module);')
            out.printf('}')
            out.printf('__box_%(box)s_initialized = false;')
            out.printf('return 0;')
        out.printf('}')

        output.includes.append('assert.h')
        output.decls.append(C_STUFF,
            data_stack=box.stack.size)

    def build_parent_ld(self, output, parent, box):
        super().build_parent_ld(output, parent, box)

        if not output.no_sections:
            out = output.sections.append(
                box_memory=box.text.memory.name,
                section='.box.%(box)s.%(box_memory)s',
                memory='box_%(box)s_%(box_memory)s')
            out.printf('__box_%(box)s_image = __%(memory)s_start;')


