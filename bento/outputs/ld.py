from .. import outputs
from ..box import Memory
import io
import textwrap
import itertools as it
import collections as co

@outputs.output
class LdOutput(outputs.Output):
    """
    Name of file to target for a linkerscript.
    """
    __argname__ = "ld"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser, **kwargs):
        super().__argparse__(parser, **kwargs)
        parser.add_argument('--no_sections', type=bool,
            help="Don't emit linker sections, not emitting sections "
                "makes it possible to include the generated linkerscript "
                "in a custom linkerscript.")
        defineparser = parser.add_set('--define')
        defineparser.add_argument('define',
            help='Add custom symbols to the linkerscript. For example: '
                '--define.__HeapLimit=__heap_end.')

    def __init__(self, path=None, no_sections=None, define={}):
        super().__init__(path)
        self.no_sections = no_sections or False
        self._defines = co.OrderedDict(sorted(
            (k, getattr(v, 'define', v)) for k, v in define.items()))

        self.decls = outputs.OutputField(self)
        self.memories = outputs.OutputField(self,
            indent=4,
            memory=None,
            addr=0,
            size=0)
        self.sections = outputs.OutputField(self,
            indent=4,
            section=None,
            memory=None,
            align=4)

    @staticmethod
    def repr_memory(memory):
        mode = ''.join(sorted(memory.mode & set('rwx')))
        return ('%(start)s'
            '%%(MEMORY)-16s (%(MODE)-3s) : '
            'ORIGIN = %%(addr)#010x, '
            'LENGTH = %%(size)#010x'
            '%(end)s' % dict(
                start='/* ' if not mode else '',
                MODE=mode.upper(),
                end=' */' if not mode else ''))

    def build_parent(self, parent, box):
        # create memories + sections for subboxes?
        for memory in box.memories:
            self.memories.append(
                self.repr_memory(memory),
                memory='box_%(box)s_'+memory.name,
                addr=memory.addr, size=memory.size)

            if not self.no_sections:
                out = self.sections.append(
                    section='.box.%(box)s.' + memory.name,
                    memory='box_%(box)s_' + memory.name,
                    noload='(NOLOAD)'*('w' in memory.mode))
                out.printf('__%(memory)s_start = .;')
                out.printf('%(section)s . %(noload)s: {')
                with out.pushindent():
                    out.printf('KEEP(*(%(section)s*))')
                out.printf('} > %(MEMORY)s')
                out.printf('. = ORIGIN(%(MEMORY)s) + '
                    'LENGTH(%(MEMORY)s);')
                out.printf('__%(memory)s_end = .;')

    def build(self, box):
        if self._defines:
            out = self.decls.append(doc='User defined symbols')
            for k, v in self._defines.items():
                out.write('%-16s = %s;' % (k, v))

        for memory in box.memoryslices:
            self.memories.append(
                self.repr_memory(memory),
                memory=memory.name,
                addr=memory.addr, size=memory.size)

        # The rest of this only deals with sections
        if self.no_sections:
            return

        constants = self.decls.append(doc='overridable constants')

        out = self.sections.append(
            section='.text',
            memory=box.text.memory.name)
        out.printf('. = ALIGN(%(align)d);')
        out.printf('__text_start = .;')
        out.printf('%(section)s . : {')
        with out.pushindent():
            out.printf('*(.text*)')
            out.printf('*(.rodata*)')
            out.printf('*(.glue_7*)')
            out.printf('*(.glue_7t*)')
            out.printf('*(.eh_frame*)')
            out.printf()
            out.printf('KEEP(*(SORT_NONE(.init)))')
            out.printf('KEEP(*(SORT_NONE(.init*)))')
            out.printf('KEEP(*(SORT_NONE(.fini)))')
            out.printf('KEEP(*(SORT_NONE(.fini*)))')
            out.printf()
            out.printf('. = ALIGN(4);')
            out.printf('PROVIDE_HIDDEN(__preinit_array_start = .);')
            out.printf('KEEP(*(SORT(.preinit_array)))')
            out.printf('PROVIDE_HIDDEN(__preinit_array_end = .);')
            out.printf()
            out.printf('. = ALIGN(4);')
            out.printf('PROVIDE_HIDDEN(__init_array_start = .);')
            out.printf('KEEP(*(SORT(.init_array.*)))')
            out.printf('PROVIDE_HIDDEN(__init_array_end = .);')
            out.printf()
            out.printf('. = ALIGN(4);')
            out.printf('PROVIDE_HIDDEN(__fini_array_start = .);')
            out.printf('KEEP(*(SORT(.fini_array.*)))')
            out.printf('PROVIDE_HIDDEN(__fini_array_end = .);')
            out.printf()
            out.printf('KEEP(*crtbegin.o(.ctors))')
            out.printf('KEEP(*crtbegin?.o(.ctors))')
            out.printf('KEEP(*(EXCLUDE_FILE(*crtend?.o *crtend.o) .ctors))')
            out.printf('KEEP(*(SORT(.ctors.*)))')
            out.printf()
            out.printf('KEEP(*crtbegin.o(.dtors))')
            out.printf('KEEP(*crtbegin?.o(.dtors))')
            out.printf('KEEP(*(EXCLUDE_FILE(*crtend?.o *crtend.o) .dtors))')
            out.printf('KEEP(*(SORT(.dtors.*)))')
        out.printf('} > %(MEMORY)s')
        out.printf('. = ALIGN(%(align)d);')
        out.printf('__text_end = .;')
        out.printf()
        out.printf('__extab_start = .;')
        out.printf('.ARM.extab : {')
        with out.indent():
            out.printf('*(.ARM.extab* .gnu.linkonce.armextab.*)')
        out.printf('} > %(MEMORY)s')
        out.printf('__extab_end = .;')
        out.printf()
        out.printf('__exidx_start = .;')
        out.printf('.ARM.exidx : {')
        with out.indent():
            out.printf('*(.ARM.exidx* .gnu.linkonce.armexidx.*)')
        out.printf('} > %(MEMORY)s')
        out.printf('__exidx_end = .;')
        out.printf()
        out.printf('. = ALIGN(%(align)d);')
        if not box.runtime.data_init_hook.link:
            out.printf('__data_init_start = .;')

        # write out ram sections
        if box.stack.size and box.stack.memory:
            constants.printf('%(symbol)-16s = DEFINED(%(symbol)s) '
                '? %(symbol)s : %(value)#010x;',
                symbol='__stack_min',
                value=box.stack.size)
            out = self.sections.append(
                section='.stack',
                memory=box.stack.memory.name)
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__stack_start = .;')
            out.printf('%(section)s . (NOLOAD) : {')
            with out.pushindent():
                out.printf('. = .;')
            out.printf('} > %(MEMORY)s')
            out.printf('. += __stack_min;')
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__stack_end = .;')

        out = self.sections.append(
            section='.data',
            memory=box.data.memory.name,
            initmemory=box.text.memory.name)
        out.printf('. = ALIGN(%(align)d);')
        out.printf('__data_start = .;')
        out.printf('%(section)s . :%(at)s {',
            at=(not box.runtime.data_init_hook.link)*' AT(__data_init_start)')
        with out.pushindent():
            out.printf('*(.data*)')
        out.printf('} > %(MEMORY)s')
        out.printf('. = ALIGN(%(align)d);')
        out.printf('__data_end = .;')
        out.printf()
        out.printf('__data_init_end = '
            'LOADADDR(%(section)s) + SIZEOF(%(section)s);')
        out.printf('ASSERT(__data_init_end <= '
            'ORIGIN(%(INITMEMORY)s) + LENGTH(%(INITMEMORY)s),')
        out.printf('    "Not enough memory in %(INITMEMORY)s for data init")')

        out = self.sections.append(
            section='.bss',
            memory=box.bss.memory.name)
        out.printf('. = ALIGN(%(align)d);')
        out.printf('__bss_start = .;')
        out.printf('__bss_start__ = .;')
        out.printf('%(section)s . (NOLOAD) : {')
        with out.pushindent():
            out.printf('*(.bss*)')
            out.printf('*(COMMON)')
        out.printf('} > %(MEMORY)s')
        out.printf('. = ALIGN(%(align)d);')
        out.printf('__bss_end = .;')
        out.printf('__bss_end__ = .;')

        if box.heap.size and box.heap.memory:
            constants.printf('%(symbol)-16s = DEFINED(%(symbol)s) '
                '? %(symbol)s : %(value)#010x;',
                symbol='__heap_min',
                value=box.heap.size)
            out = self.sections.append(
                section='.heap',
                memory=box.heap.memory.name)
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__heap_start = .;')
            out.printf('__end__ = .;')
            out.printf('PROVIDE(end = .);')
            out.printf('%(section)s . (NOLOAD) : {')
            with out.pushindent():
                out.printf('. = .;')
            out.printf('} > %(MEMORY)s')
            out.printf('. = ORIGIN(%(MEMORY)s) + LENGTH(%(MEMORY)s);')
            out.printf('. = ALIGN(%(align)d);')
            out.printf('__heap_end = .;')
            out.printf('__heap_limit = .;')
            out.printf()
            out.printf('ASSERT(__heap_end - __heap_start > __heap_min,')
            out.printf('    "Not enough memory in %(MEMORY)s for heap")')

    def getvalue(self):
        self.seek(0)
        self.printf('/***** AUTOGENERATED *****/')
        self.printf()

        if self.decls:
            for decl in self.decls:
                if 'doc' in decl:
                    for line in textwrap.wrap(decl['doc'], width=71):
                        self.print('/* %s */' % line)
                self.print(decl.getvalue().strip())
                self.print()

        if self.memories:
            self.print('MEMORY {')
            # order memories based on address
            for memory in sorted(self.memories, key=lambda m: m['addr']):
                if 'doc' in memory:
                    for line in textwrap.wrap(
                            memory['doc'], width=78-10):
                        self.print(4*' ' + '/* %s */' % line)
                self.print(4*' ' + str(memory).strip())
            self.print('}')
            self.print('')

        if self.sections and not self.no_sections:
            self.print('SECTIONS {')
            # order sections based on memories' address
            sections = self.sections
            i = 0
            for memory in sorted(self.memories, key=lambda m: m['addr']):
                if any(section['memory'] == memory['memory']
                        for section in sections):
                    with self.pushattrs(indent=4, memory=memory['memory']):
                        self.printf('/* %(MEMORY)s sections */')
                        self.printf('. = ORIGIN(%(MEMORY)s);')
                nsections = []
                for section in sections:
                    if section['memory'] == memory['memory']:
                        if 'doc' in section:
                            for line in textwrap.wrap(
                                    section['doc'], width=78-10):
                                self.print(4*' ' + '/* %s */' % line)
                        self.print(4*' ' + str(section).strip())
                        if i < len(self.sections)-1:
                            self.print()
                            i += 1
                    else:
                        nsections.append(section)
                sections = nsections
            # write any sections without a valid memory?
            if sections:
                with self.pushattrs(indent=4):
                    self.printf('/* misc sections */')
                for section in sections:
                    if 'doc' in section:
                        for line in textwrap.wrap(
                                section['doc'], width=78-10):
                            self.print(4*' ' + '/* %s */' % line)
                    self.print(4*' ' + str(section).strip())
                    if i < len(self.sections)-1:
                        self.print()
                        i += 1
            self.print('}')
            self.print()

        return super().getvalue()
