from .. import outputs
from ..box import Memory
import io
import textwrap
import itertools as it

def buildmemory(outf, memory):
    outf.pushattrs(
        memory='%(memory_prefix)s' + memory.name,
        mode=''.join(sorted(memory.mode)),
        addr=memory.addr,
        size=memory.size)
    outf.writef('%(MEMORY)-16s (%(MODE)-3s) : '
        'ORIGIN = %(addr)#010x, '
        'LENGTH = %(size)#010x')

def buildsymbol(outf, symbol):
    outf.pushattrs(
        symbol='%(symbol_prefix)s' + symbol[0],
        addr=symbol[1])
    outf.writef('%(symbol)-24s = ')
    if outf.get('cond', False):
        outf.writef('DEFINED(%(symbol)s) ? %(symbol)s : ')
    try:
        outf.writef('%(addr)#010x;')
    except TypeError:
        outf.writef('%(addr)s;')

## TODO need access to high-level output?
#def buildstack(stack, outf):
#    outf.pushattrs(mode='rw') # TODO how get mem attr??
#    outf.write('.stack (NOLOAD) : {\n')
#    with outf.pushindent():
#        outf.write('. = ALIGN(8);\n')
#        outf.write('__stack = .;\n')
#        outf.write('. += __stack_min;\n')
#        outf.write('. = ALIGN(8);\n')
#        outf.write('__stack_end = .;\n')
#    outf.write('} > %(mem)s\n')

@outputs.output('sys')
@outputs.output('box')
class PartialLDScriptOutput_(outputs.Output_):
    """
    Name of file to target for a partial linkerscript. This is the minimal
    additions needed for a bento box and should be imported into a traditional
    linkerscript to handle the normal program sections.
    """
    __argname__ = "partial_ldscript_"
    __arghelp__ = __doc__

    def __init__(self, path=None,
            symbol_prefix='__',
            section_prefix='.',
            memory_prefix=''):
        super().__init__(path)
        self.decls = outputs.OutputField_(self, {tuple: buildsymbol})
        self.memories = outputs.OutputField_(self, {Memory: buildmemory},
            indent=4,
            memory=None,
            mode='rwx',
            addr=0,
            size=0)
        self.sections = outputs.OutputField_(self,
            indent=4,
            section=None,
            memory=None,
            align=4)
        self.pushattrs(
            symbol_prefix=symbol_prefix,
            section_prefix=section_prefix,
            memory_prefix=memory_prefix)

#    def box(self, box):
#        super().box(box)
#        self.consumed = {m.name: 0 for m in box.memories}

        # create memories + sections for subboxes?
#        for subbox in box.boxes:
#            with self.pushattrs(
#                    box=subbox.name,
#                    section_prefix='.box.%(box)s.',
#                    memory_prefix='box_%(box)s_'):
#
#                for memory in subbox.memories:
#                    self.memories.append(memory)
#
#                    outf = self.sections.append(
#                        section='%(section_prefix)s' + memory.name,
#                        memory='%(memory_prefix)s' + memory.name)
#                    outf.writef('%(section)s : {\n')
#                    with outf.pushindent():
#                        # TODO prefixes considered harmful?
#                        outf.writef('__%(memory)s = .;\n')
#                        outf.writef('KEEP(*(%(section)s*))\n')
#                        outf.writef('. = ORIGIN(%(MEMORY)s) + '
#                            'LENGTH(%(MEMORY)s);\n')
#                        outf.writef('__%(memory)s_end = .;\n')
#                    outf.writef('} > %(MEMORY)s')
##
#            ldscript = LDScriptOutput_(subbox,
#                symbol_prefix='__box_%(box)s_',
#                section_prefix='.box.%(box)s.',
#                memory_prefix='box_%(box)s_')
#            self.decls.extend(ldscript.decls)
#            self.memories.extend(ldscript.memories)
#            self.sections.extend(ldscript.sections)
#
#
#            for memory in box.memories:
#
#            self.memories.append(memory)
#            self.
#            for memory in ldscript.memories:
#                self.decls.append(('%(memory)s',
#                    'ORIGIN(%(MEMORY)s)'),
#                    memory=memory['memory'])
#                self.decls.append(('%(memory)s_end',
#                    'ORIGIN(%(MEMORY)s) + LENGTH(%(MEMORY)s)'),
#                    memory=memory['memory'])

    def default_build_parent(self, parent, box):
        # create memories + sections for subboxes?
        with self.pushattrs(
                section_prefix='.box.%(box)s.',
                memory_prefix='box_%(box)s_'):

            for memory in box.memories:
                self.memories.append(memory)

                outf = self.sections.append(
                    section='%(section_prefix)s' + memory.name,
                    memory='%(memory_prefix)s' + memory.name)
                outf.writef('%(section)s : {\n')
                with outf.pushindent():
                    # TODO prefixes considered harmful?
                    outf.writef('__%(memory)s = .;\n')
                    outf.writef('KEEP(*(%(section)s*))\n')
                    outf.writef('. = ORIGIN(%(MEMORY)s) + '
                        'LENGTH(%(MEMORY)s);\n')
                    outf.writef('__%(memory)s_end = .;\n')
                outf.writef('} > %(MEMORY)s')

    def build(self, box):
        # TODO docs?
        self.write('/***** AUTOGENERATED *****/\n')
        self.write('\n')
        if self.decls:
            for decl in self.decls:
                self.write(decl.getvalue())
                self.write('\n')
            self.write('\n')
        if self.memories:
            self.write('MEMORY {\n')
            # order memories based on address
            for memory in sorted(self.memories, key=lambda m: m['addr']):
                if memory['mode']:
                    self.write(memory.getvalue())
                    self.write('\n')
            self.write('}\n')
            self.write('\n')
        if self.sections:
            self.write('SECTIONS {\n')
            # order sections based on memories' address
            sections = self.sections
            for memory in sorted(self.memories, key=lambda m: m['addr']):
                if any(section['memory'] == memory['memory']
                        for section in sections):
                    self.write('    /* %s sections */\n'
                        % memory['memory'].upper())
                nsections = []
                for section in sections:
                    if section['memory'] == memory['memory']:
                        self.write(section.getvalue())
                        self.write('\n\n')
                    else:
                        nsections.append(section)
                sections = nsections
            # write any sections without a valid memory?
            if sections:
                self.write('    /* misc sections */\n')
                for section in sections:
                    self.write(section.getvalue())
                    self.write('\n\n')
            self.write('}\n')
            self.write('\n')

@outputs.output('sys')
@outputs.output('box')
class LDScriptOutput_(PartialLDScriptOutput_):
    """
    Name of file to target for the linkerscript.
    """
    __argname__ = "ldscript_"
    __arghelp__ = __doc__

    def __init__(self, path=None,
            symbol_prefix='__',
            section_prefix='.',
            memory_prefix=''):
        super().__init__(path,
            symbol_prefix=symbol_prefix,
            section_prefix=section_prefix,
            memory_prefix=memory_prefix)

    def default_build(self, box):
        for memory in box.memories:
            for slice in memory - it.chain.from_iterable(
                    subbox.memories for subbox in box.boxes):
                self.memories.append(slice)
#
#        memories = box.memories
#        for submemory in it.chain.from_iterable(
#                subbox.memories for subbox in box.boxes):
#            nmemories = []
#            for memory in memories:
#                slices = memory - submemory
#                nmemories.extend(slices)
#            memories = nmemories
#
#        for memory in memories:
#            self.memories.append(memory)

        if box.issys():
            self.decls.insert(0, 'ENTRY(Reset_Handler)')

        # write out rom sections
        # need interrupt vector?
        if box.issys() and box.isr_vector:
            # TODO need this?
            # TODO configurable?
#            memory = box.bestmemory('rx', box.isr_vector.size,
#                consumed=self.consumed)
#            self.consumed[memory.name] += box.isr_vector.size
            memory, _, _ = box.consume('rx', box.isr_vector.size)
            self.decls.append(('isr_vector_min', box.isr_vector.size),
                cond=True)
#            self.decls.append('%(symbol)-16s = '
#                'DEFINED(%(symbol)s) ? %(symbol)s : %(size)#010x;',
#                symbol='%(symbol_prefix)s' + 'isr_vector_min',
#                size=0x400) # TODO configure this?
            outf = self.sections.append(
                section='%(section_prefix)s' + 'isr_vector',
                memory='%(memory_prefix)s' + memory.name)
            outf.writef('.isr_vector : {\n')
            with outf.pushindent():
                outf.writef('. = ALIGN(%(align)d);\n')
                outf.writef('%(symbol_prefix)sisr_vector = .;\n')
                outf.writef('KEEP(*(%(section_prefix)sisr_vector))\n')
                outf.writef('. = %(symbol_prefix)sisr_vector +'
                    '%(symbol_prefix)sisr_vector_min;\n')
                outf.writef('. = ALIGN(%(align)d);\n')
                outf.writef('%(symbol_prefix)sisr_vector_end = .;\n')
            outf.writef('} > %(MEMORY)s')

#        memory = box.bestmemory('rx', box.text.size,
#            consumed=self.consumed)
#        self.consumed[memory.name] += box.text.size
        memory, _, _ = box.consume('rx', box.text.size)
        outf = self.sections.append(
            section='%(section_prefix)s' + 'text',
            memory='%(memory_prefix)s' + memory.name)
        outf.writef('%(section)s : {\n')
        with outf.pushindent():
            outf.writef('. = ALIGN(%(align)d);\n')
            outf.writef('%(symbol_prefix)stext = .;\n')
            outf.writef('*(%(section_prefix)stext*)\n')
            outf.writef('*(%(section_prefix)srodata*)\n')
            outf.writef('*(%(section_prefix)sglue_7*)\n')
            outf.writef('*(%(section_prefix)sglue_7t*)\n')
            outf.writef('*(%(section_prefix)seh_frame*)\n')
            outf.writef('KEEP(*(%(section_prefix)sinit*))\n')
            outf.writef('KEEP(*(%(section_prefix)sfini*))\n') # TODO oh boy there's a lot of other things
            outf.writef('. = ALIGN(%(align)d);\n')
            outf.writef('%(symbol_prefix)stext_end = .;\n')
            outf.writef('%(symbol_prefix)sdata_init = .;\n')
        outf.writef('} > %(MEMORY)s')

        # writef out ram sections
        if box.stack:
#            memory = box.bestmemory('rw', box.stack.size,
#                consumed=self.consumed)
#            self.consumed[memory.name] += box.stack.size
            memory, _, _ = box.consume('rw', box.stack.size)
            self.decls.append(('stack_min', box.stack.size),
                cond=True)
#            self.decls.append('%(symbol)-16s = '
#                'DEFINED(%(symbol)s) ? %(symbol)s : %(size)#010x;',
#                symbol='%(symbol_prefix)s' + 'stack_min',
#                size=box.stack.size)
            outf = self.sections.append(
                section='%(section_prefix)s' + 'stack',
                memory='%(memory_prefix)s' + memory.name)
            outf.writef('%(section)s (NOLOAD) : {\n')
            with outf.pushindent():
                outf.writef('. = ALIGN(%(align)d);\n')
                outf.writef('%(symbol_prefix)sstack = .;\n')
                outf.writef('. += %(symbol_prefix)sstack_min;\n')
                outf.writef('. = ALIGN(%(align)d);\n')
                outf.writef('%(symbol_prefix)sstack_end = .;\n')
            outf.writef('} > %(MEMORY)s')

#        memory = box.bestmemory('rw', box.data.size,
#            consumed=self.consumed)
#        self.consumed[memory.name] += box.data.size
        memory, _, _ = box.consume('rw', box.data.size)
        outf = self.sections.append(
            section='%(section_prefix)s' + 'data',
            memory='%(memory_prefix)s' + memory.name)
        outf.writef('%(section)s : AT(%(symbol_prefix)sdata_init) {\n')
        with outf.pushindent():
            outf.writef('. = ALIGN(%(align)d);\n')
            outf.writef('%(symbol_prefix)sdata = .;\n')
            outf.writef('*(%(section_prefix)sdata*)\n')
            outf.writef('. = ALIGN(%(align)d);\n')
            outf.writef('%(symbol_prefix)sdata_end = .;\n')
        outf.writef('} > %(MEMORY)s')

#        memory = box.bestmemory('rw', box.bss.size,
#            consumed=self.consumed)
#        self.consumed[memory.name] += box.bss.size
        memory, _, _ = box.consume('rw', box.bss.size)
        outf = self.sections.append(
            section='%(section_prefix)s' + 'bss',
            memory='%(memory_prefix)s' + memory.name)
        outf.writef('%(section)s (NOLOAD) : {\n')
        with outf.pushindent():
            outf.writef('. = ALIGN(%(align)d);\n')
            outf.writef('%(symbol_prefix)sbss = .;\n')
            # TODO hm
            outf.writef('%(symbol_prefix)sbss_start__ = .;\n')
            outf.writef('*(%(section_prefix)sbss*)\n')
            if outf['section_prefix'] == '.':
                outf.writef('*(COMMON)\n')
            outf.writef('. = ALIGN(%(align)d);\n')
            outf.writef('%(symbol_prefix)sbss_end = .;\n')
            outf.writef('%(symbol_prefix)sbss_end__ = .;\n')
        outf.writef('} > %(MEMORY)s')

        if box.heap:
#            memory = box.bestmemory('rw', box.heap.size,
#                consumed=self.consumed)
#            self.consumed[memory.name] += box.heap.size
            memory, _, _ = box.consume('rw', box.heap.size)
            self.decls.append(('heap_min', box.heap.size),
                cond=True)
            outf = self.sections.append(
                section='%(section_prefix)s' + 'heap',
                memory='%(memory_prefix)s' + memory.name)
            outf.writef('%(section)s (NOLOAD) : {\n')
            with outf.pushindent():
                outf.writef('. = ALIGN(%(align)d);\n')
                if outf['section_prefix'] == '.':
                    outf.writef('__end__ = .;\n')
                    outf.writef('PROVIDE(end = .);\n')
                outf.writef('%(symbol_prefix)sheap = .;\n')
                # TODO need all these?
                outf.writef('%(symbol_prefix)sHeapBase = .;\n')
                outf.writef('. += ORIGIN(%(MEMORY)s) + LENGTH(%(MEMORY)s);\n')
                outf.writef('. = ALIGN(%(align)d);\n')
                outf.writef('%(symbol_prefix)sheap_end = .;\n')
                # TODO need all these?
                outf.writef('%(symbol_prefix)sHeapLimit = .;\n')
                outf.writef('%(symbol_prefix)sheap_limit = .;\n')
            outf.writef('} > %(MEMORY)s\n')
            outf.writef('ASSERT(%(symbol_prefix)sheap_end - '
                '%(symbol_prefix)sheap > %(symbol_prefix)sheap_min,\n')
            outf.writef('    "Not enough memory for heap")')

#@outputs.output('sys')
#@outputs.output('box')
#class LinkerScriptOutput(outputs.Output):
#    """
#    Name of file to target for the linkerscript.
#    """
#    __argname__ = "ldscript"
#    __arghelp__ = __doc__
#
#    def __init__(self, sys, box, path):
#        self._decls = []
#        self._memories = []
#        self._sections = []
#        super().__init__(sys, box, path)
#
#    def append_decl(self, fmt=None, **kwargs):
#        outf = self.mkfield(**kwargs)
#        self._decls.append(outf)
#        if fmt is not None:
#            outf.writef(fmt)
#        return outf
#
#    def append_memory(self, fmt=None, **kwargs):
#        outf = self.mkfield(**kwargs)
#        self._memories.append(outf)
#        if fmt is not None:
#            outf.writef(fmt)
#        return outf
#
#    def append_section(self, fmt=None, **kwargs):
#        outf = self.mkfield(**kwargs)
#        self._sections.append(outf)
#        if fmt is not None:
#            outf.write(fmt)
#        return outf
#
#    def build(self, outf):
#        outf.write('/***** AUTOGENERATED *****/\n')
#        outf.write('\n')
#        if self._decls:
#            for decl in self._decls:
#                outf.write(decl.getvalue())
#                outf.write('\n')
#            outf.write('\n')
#        if self._memories:
#            outf.write('MEMORY {\n')
#            for memory in self._memories:
#                for line in memory.getvalue().strip().split('\n'):
#                    outf.write(4*' ' + line + '\n')
#            outf.write('}\n')
#            outf.write('\n')
#        if self._sections:
#            outf.write('SECTIONS {\n')
#            for i, section in enumerate(self._sections):
#                for line in section.getvalue().strip().split('\n'):
#                    outf.write(4*' ' + line + '\n')
#                if i < len(self._sections)-1:
#                    outf.write('\n')
#            outf.write('}\n')
#            outf.write('\n')
#
#@outputs.output('sys')
#@outputs.output('box')
#class PartialLinkerScriptOutput(LinkerScriptOutput):
#    """
#    Name of file to target for a partial linkerscript. This is the minimal
#    additions needed for a bento box and should be imported into a traditional
#    linkerscript to handle the normal program sections.
#    """
#    __argname__ = "partial_ldscript"
#    __arghelp__ = __doc__
