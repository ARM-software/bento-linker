from .. import outputs
from ..box import Memory
import io
import textwrap
import itertools as it
import collections as co

@outputs.output
class LDOutput(outputs.Output):
    """
    Name of file to target for a linkerscript.
    """
    __argname__ = "ld"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser, **kwargs):
        outputs.Output.__argparse__(parser, **kwargs)
        parser.add_argument('--no_sections', type=bool,
            help='Don\'t emit sections, this makes it possible to include '
                'the generated linkerscript in a custom linkerscript.')
        defineparser = parser.add_set('--defines', metavar='DEFINE')
        defineparser.add_argument('define',
            help='Add custom symbols to the linkerscript. For example: '
                'define.__HeapLimit=__heap_end.')

    def __init__(self, path=None, no_sections=False, defines={}):
        super().__init__(path)
        self.no_sections = no_sections
        self._defines = co.OrderedDict(sorted(
            (k, getattr(v, 'define', v)) for k, v in defines.items()))

        def buildmemory(out, memory):
            out.pushattrs(
                prefix=out.get('prefix', ''),
                memory='%(prefix)s' + memory.name,
                mode=''.join(sorted(memory.mode)),
                addr=memory.addr,
                size=memory.size)
            out.writef('%(MEMORY)-16s (%(MODE)-3s) : '
                'ORIGIN = %(addr)#010x, '
                'LENGTH = %(size)#010x')

        self.decls = outputs.OutputField(self)
        self.memories = outputs.OutputField(self, {Memory: buildmemory},
            indent=4,
            memory=None,
            mode='rwx',
            addr=0,
            size=0)
        self.sections = outputs.OutputField(self,
            indent=4,
            section=None,
            memory=None,
            align=4)

    def default_build_box(self, box):
        if self._defines:
            out = self.decls.append(doc='User defined symbols')
            for k, v in self._defines.items():
                out.write('%-16s = %s;' % (k, v))

        for memory in box.memoryslices:
            self.memories.append(memory)

        # The rest of this only deals with sections
        if self.no_sections:
            return

        constants = self.decls.append(doc='overridable constants')

        out = self.sections.append(
            section='.text',
            memory=box.text.memory.name)
        out.printf('%(section)s : {')
        with out.pushindent():
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__text = .;')
            out.printf('*(.text*)')
            out.printf('*(.rodata*)')
            out.printf('*(.glue_7*)')
            out.printf('*(.glue_7t*)')
            out.printf('*(.eh_frame*)')
            out.printf('KEEP(*(.init*))')
            out.printf('KEEP(*(.fini*))') # TODO oh boy there's a lot of other things
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__text_end = .;')
            out.printf('__data_init = .;')
        out.printf('} > %(MEMORY)s')

        # write out ram sections
        if box.stack:
            constants.printf('%(symbol)-16s = DEFINED(%(symbol)s) '
                '? %(symbol)s : %(value)#010x;',
                symbol='__stack_min',
                value=box.stack.size)
            out = self.sections.append(
                section='.stack',
                memory=box.stack.memory.name)
            out.printf('%(section)s (NOLOAD) : {')
            with out.pushindent():
                out.printf('. = ALIGN(%(align)d);')
                out.printf('__stack = .;')
                out.printf('. += __stack_min;')
                out.printf('. = ALIGN(%(align)d);')
                out.printf('__stack_end = .;')
            out.printf('} > %(MEMORY)s')

        out = self.sections.append(
            section='.data',
            memory=box.data.memory.name)
        out.printf('%(section)s : AT(__data_init) {')
        with out.pushindent():
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__data = .;')
            out.printf('*(.data*)')
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__data_end = .;')
        out.printf('} > %(MEMORY)s')

        out = self.sections.append(
            section='.bss',
            memory=box.bss.memory.name)
        out.printf('%(section)s (NOLOAD) : {')
        with out.pushindent():
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__bss = .;')
            # TODO hm
            out.printf('__bss_start__ = .;')
            out.printf('*(.bss*)')
            out.printf('*(COMMON)')
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__bss_end = .;')
            out.printf('__bss_end__ = .;')
        out.printf('} > %(MEMORY)s')

        if box.heap:
            constants.printf('%(symbol)-16s = DEFINED(%(symbol)s) '
                '? %(symbol)s : %(value)#010x;',
                symbol='__heap_min',
                value=box.heap.size)
            out = self.sections.append(
                section='.heap',
                memory=box.heap.memory.name)
            out.printf('%(section)s (NOLOAD) : {')
            with out.pushindent():
                out.printf('. = ALIGN(%(align)d);')
                out.printf('__end__ = .;')
                out.printf('PROVIDE(end = .);')
                out.printf('__heap = .;')
                # TODO need all these?
                out.printf('__HeapBase = .;')
                out.printf('. += ORIGIN(%(MEMORY)s) + LENGTH(%(MEMORY)s);')
                out.printf('. = ALIGN(%(align)d);')
                out.printf('__heap_end = .;')
                # TODO need all these?
                out.printf('__HeapLimit = .;')
                out.printf('__heap_limit = .;')
            out.printf('} > %(MEMORY)s')
            out.printf()
            out.printf('ASSERT(__heap_end - __heap > __heap_min,')
            out.printf('    "Not enough memory for heap")')

    def default_build_parent(self, parent, box):
        # create memories + sections for subboxes?
        for memory in box.memories:
            self.memories.append(memory, prefix='box_%(box)s_')

            if not self.no_sections:
                out = self.sections.append(
                    section='.box.%(box)s.' + memory.name,
                    memory='box_%(box)s_' + memory.name)
                out.printf('%(section)s : {')
                with out.pushindent():
                    out.printf('__%(memory)s = .;')
                    out.printf('KEEP(*(%(section)s*))')
                    out.printf('. = ORIGIN(%(MEMORY)s) + '
                        'LENGTH(%(MEMORY)s);')
                    out.printf('__%(memory)s_end = .;')
                out.printf('} > %(MEMORY)s')

    def build(self, box):
        # TODO docs?
        self.write('/***** AUTOGENERATED *****/\n')
        self.write('\n')
        if self.decls:
            for decl in self.decls:
                if 'doc' in decl:
                    for line in textwrap.wrap(decl['doc'], width=72):
                        self.write('/* %s */\n' % line)
                self.write(decl.getvalue().strip())
                self.write('\n\n')
        if self.memories:
            self.write('MEMORY {\n')
            # order memories based on address
            for memory in sorted(self.memories, key=lambda m: m['addr']):
                if memory['mode']:
                    if 'doc' in memory:
                        for line in textwrap.wrap(memory['doc'], width=68):
                            self.write(4*' '+'/* %s */\n' % line)
                    self.write(4*' ')
                    self.write(memory.getvalue().strip())
                    self.write('\n')
            self.write('}\n')
            self.write('\n')
        if self.sections:
            self.write('SECTIONS {\n')
            # order sections based on memories' address
            sections = self.sections
            i = 0
            for memory in sorted(self.memories, key=lambda m: m['addr']):
                if any(section['memory'] == memory['memory']
                        for section in sections):
                    self.write('    /* %s sections */\n'
                        % memory['memory'].upper())
                nsections = []
                for section in sections:
                    if section['memory'] == memory['memory']:
                        if 'doc' in section:
                            for line in textwrap.wrap(section['doc'],
                                    width=68):
                                self.write(4*' '+'/* %s */\n' % line)
                        self.write(4*' ')
                        self.write(section.getvalue().strip())
                        self.write('\n')
                        if i < len(self.sections)-1:
                            self.write('\n')
                            i += 1
                    else:
                        nsections.append(section)
                sections = nsections
            # write any sections without a valid memory?
            if sections:
                self.write('    /* misc sections */\n')
                for section in sections:
                    if 'doc' in section:
                        for line in textwrap.wrap(section['doc'],
                                width=68):
                            self.write(4*' '+'/* %s */\n' % line)
                    self.write(4*' ')
                    self.write(section.getvalue().strip())
                    self.write('\n')
                    if i < len(self.sections)-1:
                        self.write('\n')
                        i += 1
            self.write('}\n')
            self.write('\n')

