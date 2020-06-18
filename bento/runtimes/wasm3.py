from .. import runtimes
import itertools as it

WASI_API = '''
m3ApiRawFunction(__box_hook_wasi_fd_close) {
    // close not supported
    assert(false);
}

m3ApiRawFunction(__box_hook_wasi_fd_seek) {
    // seek not supported
    assert(false);
}

m3ApiRawFunction(__box_hook_wasi_fd_fdstat_get) {
    struct fdstat {
        uint8_t  filetype;
        uint16_t flags;
        uint64_t rights_base;
        uint64_t rights_inheriting;
    };

    m3ApiGetArg(uint32_t, fd);
    (void)fd;
    m3ApiGetArgMem(struct fdstat*, fdstat);

    fdstat->filetype = 2; // filetype = character device
    fdstat->flags = 0;
    fdstat->rights_base = 0;
    fdstat->rights_inheriting = 0;

    m3ApiReturnType(int32_t);
    m3ApiReturn(0);
}

m3ApiRawFunction(__box_hook_wasi_fd_write) {
    struct iov {
        uint32_t base_ptr;
        uint32_t size;
    };

    m3ApiGetArg(uint32_t, fd);
    m3ApiGetArgMem(struct iov*, iovs);
    m3ApiGetArg(uint32_t, iovs_len);
    m3ApiGetArgMem(uint32_t*, nwritten);

    // only stdout or stderr
    assert(fd == 1 || fd == 2);
    uint32_t total = 0;
    for (int i = 0; i < iovs_len; i++) {
        for (int j = 0; j < iovs[i].size; j++) {
            uint8_t c = *(char*)m3ApiOffsetToPtr(iovs[i].base_ptr + j);
            //printf("%c", c);
            putchar(c);
            if (c == '\\n') {
                fflush(stdout);
            }
        }
    }

    *nwritten = total;
    m3ApiReturnType(int32_t);
    m3ApiReturn(0);
}
'''


@runtimes.runtime
class Wasm3Runtime(runtimes.Runtime):
    """
    A bento-box runtime using wasm3, a wasm interpreter
    """
    __argname__ = "wasm3"
    __arghelp__ = __doc__

    def build_common_header(self, sys, box, output):
        output.append_include("<sys/types.h>")

        # TODO error if import not found?
        output.append_decl('// exports from box %s' % box.name)
        for export in box.exports.values():
            assert len(export.rets) <= 1
            output.append_decl('extern %(ret)s %(name)s(%(args)s);' % dict(
                name=export.name,
                args='void' if not export.args else ', '.join(
                    '%s %s' % arg for arg in zip(
                        export.args, util.arbitrary())),
                ret='void' if not export.rets else export.rets[0]))
        output.append_decl('')

        # TODO error if import not found?
        output.append_decl('// imports from box %s' % box.name)
        for import_ in box.imports.values():
            assert len(import_.rets) <= 1
            output.append_decl('extern %(ret)s %(name)s(%(args)s);' % dict(
                name=import_.name,
                args='void' if not import_.args else ', '.join(
                    '%s %s' % arg for arg in zip(
                        import_.args, util.arbitrary())),
                ret='void' if not import_.rets else import_.rets[0]))
        output.append_decl('')

    def build_sys_header(self, sys, box, output):
        """Build system header"""
        outf = output.append_decl()
        outf.write('// jumptable initialization\n')
        outf.write('void __box_%s_init(void);\n' % box.name)

        self.build_common_header(sys, box, output)

    def build_sys_jumptable_prologue(self, sys, output):
        output.append_include("<wasm3/wasm3.h>")
        output.append_include("<wasm3/m3_api_defs.h>")
        output.append_include("<wasm3/m3_env.h>")

        outf = output.append_decl()
        outf.write('// GCC stdlib hook\n')
        outf.write('extern int _write(int handle, char *buffer, int size);\n')

    def build_sys_jumptable(self, sys, box, output):
        self.build_common_header(sys, box, output)

        output.append_decl('IM3Runtime __box_%s_runtime;' % box.name)
        output.append_decl('IM3Module __box_%s_module;' % box.name)
        output.append_decl()

        # TODO configure me
        output.append_decl('#define __BOX_%s_STACK %d' % (
            box.name.upper(), box.sections['stack'].size))
        output.append_decl()

        output.append_decl('// wasm3 import hooks')
        output.append_decl(WASI_API.lstrip())

        for import_ in box.imports.values():
            outf = output.append_decl()
            outf.write('m3ApiRawFunction(__box_hook_%s) {\n' % import_.name)
            for i, type in enumerate(import_.args):
                assert type.count('*') in {0, 1}
                if '*' in type:
                    outf.write(4*' '+'m3ApiGetArgMem(%s, %s);\n' % (
                        type, 'a%d' % i))
                else:
                    outf.write(4*' '+'m3ApiGetArg(%s, %s);\n' % (
                        type, 'a%d' % i))
            outf.write(4*' '+'%(retassign)s%(name)s(%(args)s);\n' % dict(
                retassign = '%s r0 = ' % import_.rets[0]
                    if import_.rets else '',
                name=import_.name,
                args=', '.join('a%d' % i for i in range(len(import_.args)))))
            if import_.rets:
                assert len(import_.rets) == 1
                outf.write(4*' '+'m3ApiReturnType(%s);\n' % import_.rets[0])
                outf.write(4*' '+'m3ApiReturn(r0);\n')
            else:
                outf.write(4*' '+'m3ApiSuccess();\n')
            outf.write('}\n')

        output.append_decl('// wasm3 export hooks')
        for export in box.exports.values():
            outf = output.append_decl()
            outf.write('extern %(ret)s %(name)s(%(args)s) {\n' % dict(
                name=export.name,
                args='void' if not export.args else ', '.join(
                    '%s a%d' % arg for arg in zip(
                        export.args, it.count())),
                ret='void' if not export.rets else export.rets[0]))
            outf.write(4*' '+'M3Result err;\n')
            outf.write(4*' '+'IM3Function f;\n')
            outf.write(4*' '+'err = m3_FindFunction('
                '&f, __box_%s_runtime, "%s");\n' %
                (box.name, export.name))
            outf.write(4*' '+'assert(!err);\n')
            # NOTE these are internal APIs, otherwise wasm3 requires
            # string parsing
            outf.write(4*' '+'assert(f->compiled);\n')
            outf.write(4*' '+'IM3FuncType ftype = f->funcType;\n')
            outf.write(4*' '+'assert(ftype->numArgs == %d);\n' %
                len(export.args))
            outf.write(4*' '+'void *stack = __box_%s_runtime->stack;\n' %
                box.name)
            # TODO assert on type, one of c_m3Type_i32,i64,f32,f64
            for i, type in enumerate(export.args):
                assert type.count('*') in {0, 1}
                if '*' in type:
                    # TODO WTF IS _mem
                    outf.write(4*' '+'*(%(type)s*)&((uint64_t*)'
                        'stack)[%(i)s] = (uint8_t*)%(name)s - m3MemData(__box_%(box)s_runtime->memory.mallocated);\n' % dict(
                        box=box.name,
                        type=type,
                        i=i,
                        name='a%d' % i))
                else:
                    outf.write(4*' '+'*(%(type)s*)&((uint64_t*)'
                        'stack)[%(i)s] = %(name)s;\n' % dict(
                        type=type,
                        i=i,
                        name='a%d' % i))
            outf.write(4*' '+'m3StackCheckInit();\n')
            outf.write(4*' '+'''err = (M3Result)Call(
                f->compiled,
                (m3stack_t)stack,
                __box_%s_runtime->memory.mallocated,
                d_m3OpDefaultArgs);\n''' % box.name)
            outf.write(4*' '+'assert(!err);\n')
            if export.rets:
                assert len(export.rets) == 1
                outf.write(4*' '+'return *(%s*)stack;\n' % export.rets[0])
            outf.write('}\n')


        # TODO move this to init
        output.append_decl('// wasm3 init')
        outf = output.append_decl()
        outf.write('void __box_%s_init(void) {\n' % box.name)
        outf.write(4*' '+'M3Result err;\n')
        outf.write(4*' '+'IM3Environment env = m3_NewEnvironment();\n')
        outf.write(4*' '+'assert(env);\n')
        outf.write(4*' '+'__box_%s_runtime = m3_NewRuntime('
            'env, __BOX_%s_STACK, NULL);\n' % (box.name, box.name.upper()))
        outf.write(4*' '+'assert(__box_%s_runtime);\n' % box.name)
#TODO
##ifdef WASM_MEMORY_LIMIT
#    runtime->memoryLimit = WASM_MEMORY_LIMIT;
##endif
        outf.write(4*' '+'extern uint8_t __box_%s_image;\n' % box.name)
        outf.write(4*' '+'extern uint8_t __box_%s_image_end;\n' % box.name)
        outf.write(4*' '+'err = m3_ParseModule('
            'env, &__box_%(box)s_module, '
            '&__box_%(box)s_image, '
            '&__box_%(box)s_image_end - &__box_%(box)s_image);\n' % dict(
            box=box.name))
        outf.write(4*' '+'assert(!err);\n')
        outf.write(4*' '+'err = m3_LoadModule('
            '__box_%(box)s_runtime, __box_%(box)s_module);\n' % dict(
            box=box.name))
        outf.write(4*' '+'assert(!err);\n')
        outf.write('\n')

        # WASI imports (only for printf)
        for name, type in [
                ('fd_close',        'i(i)'),
                ('fd_seek',         'i(iIi*)'),
                ('fd_fdstat_get',   'i(i*)'),
                ('fd_write',        'i(i*i*)')]:
            # TODO need SuppressLookupFailure?
            outf.write(4*' '+'err = m3_LinkRawFunction('
                '__box_%(box)s_module, "%(module)s", '
                '"%(name)s", "%(type)s", '
                '&__box_hook_wasi_%(name)s);\n' % dict(
                box=box.name,
                module='wasi_snapshot_preview1', # TODO fix this
                name=name,
                type=type))

        # other imports
        for import_ in box.imports.values():
            outf.write(4*' '+'err = m3_LinkRawFunction('
                '__box_%s_module, "*", "%s", "%s(%s)", &__box_hook_%s);\n' % (
                box.name,
                import_.name,
                'i' if import_.rets else 'v',
                'i'*len(import_.args), # TODO type me
                import_.name))
            outf.write(4*' '+'assert(!err);\n')
        outf.write('}\n')

    def build_header(self, sys, box, output):
        self.build_common_header(sys, box, output)

#    def build_jumptable(self, sys, box, output):
#        self.build_common_header(sys, box, output)
#
##        output.append_decl(BOX_INIT.lstrip() % dict(name=box.name))
##        output.append_decl(BOX_WRITE.lstrip() % dict(name=box.name))
#
#        output.append_decl('extern uint32_t __stack_end;')
#        outf = output.append_decl()
#        outf.write('__attribute__((section(".jumptable")))\n')
#        outf.write('__attribute__((used))\n')
#        outf.write('const struct %(name)s_exportjumptable '
#            '__%(name)s_exportjumptable = {\n' % dict(name=box.name))
#        # special entries for the sp and __box_init
#        outf.write('    &__stack_end,\n')
#        outf.write('    __box_%s_init,\n' % box.name)
#        for export in box.exports.values():
#            outf.write('    %s,\n' % export.name)
#        outf.write('};\n')

    def build_sys_partiallinkerscript(self, sys, box, output):
        # TODO don't use RAM?
        # create memories
        for memory in box.memories.values():
            output.append_memory('%(name)-16s (%(mode)s) : '
                'ORIGIN = %(origin)#010x, '
                'LENGTH = %(length)#010x' % dict(
                    name='BOX_%s_%s' % (box.name.upper(), memory.name.upper()),
                    mode=''.join(c.upper() for c in sorted(memory.mode)),
                    origin=memory.start or 0,
                    length=memory.size))

        # create image section
        bestmemory = (sorted(
            [m for m in box.memories.values()
            if set('rx').issubset(m.mode)],
            key=lambda m: ('w' in m.mode)*(2<<32) - m.size)
                +[None])[0]
        #align = 4

        outf = output.append_section()
        outf.write('.box.%s.image : {\n' % box.name)
        #outf.write(4*' '+'. = ALIGN(%d);\n' % align)
        outf.write(4*' '+'__box_%s_image = .;\n' % box.name)
        outf.write(4*' '+'KEEP(*(.box.%s.image*))\n' % box.name)
        #outf.write(4*' '+'. = ALIGN(%d);\n' % align)
        outf.write(4*' '+'__box_%s_image_end = .;\n' % box.name)
        outf.write('} > BOX_%s_%s\n' % (box.name.upper(),
            bestmemory.name.upper() if bestmemory else '?'))

#    def build_partiallinkerscript(self, sys, box, output):
#        # create box calls for imports
#        output.append_decl('/* box calls */')
#        for i, import_ in enumerate(it.chain(
#                ['__box_fault', '__box_write'], box.imports)):
#            output.append_decl('%-16s = 0x0fffc000 + %d*2;' % (
#                import_, i))

#    def build_linkerscript(self, sys, box, output):
#        # extra decls?
#        for section in box.sections.values():
#            if section.size is not None:
#                output.append_decl('%-16s = %#010x;' % (
#                    '__%s_min' % section.name, section.size))
#
#        output.append_decl()
#        self.build_partiallinkerscript(sys, box, output)
#
#        # create memories
#        for memory in box.memories.values():
#            output.append_memory('%(name)-16s (%(mode)s) : '
#                'ORIGIN = %(origin)#010x, '
#                'LENGTH = %(length)#010x' % dict(
#                    name=memory.name.upper(),
#                    mode=''.join(c.upper() for c in sorted(memory.mode)),
#                    origin=memory.start or 0,
#                    length=memory.size))
#
#        # create sections
#        for name in ['text', 'data', 'bss'] + sorted(
#                name for name in box.sections
#                if name not in {'text', 'bss', 'data', 'heap', 'stack'}):
#            section = box.sections.get(name)
#            align = (section.align if section else 4) or 4
#            bestmemory = None
#            for memory in box.memories.values():
#                if memory.sections is not None and name in memory.sections:
#                    bestmemory = memory
#                    break
#            else:
#                if name in {'text'}:
#                    bestmemory = (sorted(
#                        [m for m in box.memories.values()
#                        if set('rx').issubset(m.mode)],
#                        key=lambda m: ('w' in m.mode)*(2<<32) - m.size)
#                            +[None])[0]
#                elif name in {'data', 'bss'}:
#                    bestmemory = (sorted(
#                        [m for m in box.memories.values()
#                        if set('rw').issubset(m.mode)],
#                        key=lambda m: -m.size)
#                            +[None])[0]
#
#            outf = output.append_section()
#            outf.write('.%(name)s%(type)s :%(at)s {\n' % dict(
#                name=name,
#                type=' (NOLOAD)' if name == 'bss' else '',
#                at=' AT(__data_init)' if name == 'data' else ''))
#            outf.write(4*' '+'. = ALIGN(%d);\n' % align)
#            outf.write(4*' '+'__%s = .;\n' % name)
#            if name == 'text':
#                outf.write(4*' '+'__jumptable = .;\n')
#                outf.write(4*' '+'KEEP(*(.jumptable))\n')
#            outf.write(4*' '+'*(.%s*)\n' % name)
#            if name == 'text':
#                outf.write(4*' '+'*(.rodata*)\n')
#                outf.write(4*' '+'KEEP(*(.init))\n') # TODO can these be wildcarded?
#                outf.write(4*' '+'KEEP(*(.fini))\n')
#            elif name == 'bss':
#                outf.write(4*' '+'*(COMMON)\n') # TODO need this?
#            outf.write(4*' '+'. = ALIGN(%d);\n' % align)
#            outf.write(4*' '+'__%s_end = .;\n' % name)
#            if name == 'text':
#                outf.write(4*' '+'__data_init = .;\n')
#            outf.write('} > %s\n' % (
#                bestmemory.name.upper() if bestmemory else '?'))
#
#        # here we handle heap/stack separately, they're a bit special since
#        # the heap/stack can "share" memory
#        heapsection = box.sections.get('heap')
#        heapalign = (heapsection.align if heapsection else 8) or 8
#        heapsize = heapsection.size
#        stacksection = box.sections.get('stack')
#        stackalign = (stacksection.align if stacksection else 8) or 8
#        stacksize = stacksection.size
#        bestmemory = None
#        for memory in box.memories.values():
#            if memory.sections is not None and 'heap' in memory.sections:
#                bestmemory = memory
#        else:
#            bestmemory = (sorted(
#                [m for m in box.memories.values()
#                if set('rw').issubset(m.mode)],
#                key=lambda m: -m.size)
#                    +[None])[0]
#
#        outf = output.append_section()
#        outf.write('.heap (NOLOAD) : {\n')
#        outf.write(4*' '+'. = ALIGN(%d);\n' % heapalign)
#        outf.write(4*' '+'__heap = .;\n')
#        outf.write(4*' '+'__stack = .;\n')
#        # TODO do we need _all_ of these?
#        outf.write(4*' '+'__end__ = .;\n') 
#        outf.write(4*' '+'PROVIDE(end = .);\n') 
#        outf.write(4*' '+'__HeapBase = .;\n')
#        outf.write(4*' '+'__HeapLimit = ('
#            'ORIGIN(%(MEM)s) + LENGTH(%(MEM)s));\n' % dict(
#                MEM=bestmemory.name.upper() if bestmemory else '?'))
#        outf.write(4*' '+'__heap_limit = ('
#            'ORIGIN(%(MEM)s) + LENGTH(%(MEM)s));\n' % dict(
#                MEM=bestmemory.name.upper() if bestmemory else '?'))
#        outf.write(4*' '+'__heap_end = ('
#            'ORIGIN(%(MEM)s) + LENGTH(%(MEM)s));\n' % dict(
#                MEM=bestmemory.name.upper() if bestmemory else '?'))
#        outf.write(4*' '+'__stack_end = ('
#            'ORIGIN(%(MEM)s) + LENGTH(%(MEM)s));\n' % dict(
#                MEM=bestmemory.name.upper() if bestmemory else '?'))
#        outf.write('} > %s' % (bestmemory.name.upper() if bestmemory else '?'))
#        if heapsize or stacksize:
#            outf.write('\n\n')
#            outf.write('ASSERT(__HeapLimit - __HeapBase > %s,\n' %
#                '__heap_min + __stack_min' if heapsize and stacksize else
#                '__heap_min' if heapsize else
#                '__stack_min')
#            outf.write(4*' '+'"Not enough memory remains for heap and stack")')
