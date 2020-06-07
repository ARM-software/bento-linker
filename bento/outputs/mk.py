from .. import outputs
import textwrap
import re
import os
import itertools as it
import collections as co

@outputs.output
class MKOutput(outputs.Output):
    """
    Name of file to target for a box-specific Makefile. This makes some
    assumptions about the cross compiler (GCC) and is really only intended
    for demos. Feel free to omit or modify after generation.
    """
    __argname__ = "mk"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser, **kwargs):
        outputs.Output.__argparse__(parser, **kwargs)

        defineparser = parser.add_set('--defines',
            append=True, metavar='DEFINE')
        defineparser.add_argument('define',
            help='Add preprocessor defines to the build.')
        parser.add_argument('--libs', type=list,
            help='Override libraries. Defaults to '
                '[\'m\', \'c\', \'gcc\', and \'nosys\'].')

        parser.add_argument('--target',
            help='Override the target output (name.elf) for the makefile.')
        parser.add_argument('--cross_compile',
            help='Override the compiler triplet (arm-none-eabi-) '
                'for the makefile.')
        parser.add_argument('--cc',
            help='Override the C compiler for the makefile.')
        parser.add_argument('--objcopy',
            help='Override the obcopy program for the makefile.')
        parser.add_argument('--objdump',
            help='Override the objdump program for the makefile.')
        parser.add_argument('--ar',
            help='Override the ar program for the makefile.')
        parser.add_argument('--size',
            help='Override the size program for the makefile.')
        parser.add_argument('--gdb',
            help='Override the gdb program for the makefile.')
        parser.add_argument('--gdbaddr',
            help='Override the gdb addr (localhost) for the makefile.')
        parser.add_argument('--gdbport',
            help='Override the gdb port (3333) for the makefile.')
        parser.add_argument('--tty',
            help='Override the tty file (/dev/tty*) for the makefile.')
        parser.add_argument('--baud',
            help='Override the baud rate (115200) for the makefile.')

        parser.add_argument('--cflags', type=list,
            help='Add custom C flags.')
        parser.add_argument('--asmflags', type=list,
            help='Add custom assembly flags.')
        parser.add_argument('--lflags', type=list,
            help='Add custom linker flags.')

    def __init__(self, path=None, defines={}, libs=None,
            target=None, cross_compile=None,
            cc=None, objcopy=None, objdump=None, ar=None,
            size=None, gdb=None, gdbaddr=None, gdbport=None,
            tty=None, baud=None,
            cflags=None, asmflags=None, lflags=None):
        super().__init__(path)
        self._defines = co.OrderedDict(sorted(
            (k, getattr(v, 'define', v)) for k, v in defines.items()))
        self._libs = libs or ['m', 'c', 'gcc', 'nosys']

        self._target = target
        self._cross_compile = cross_compile or 'arm-none-eabi-'
        self._cc = cc or '$(CROSS_COMPILE)gcc'
        self._objcopy = objcopy or '$(CROSS_COMPILE)objcopy'
        self._objdump = objdump or '$(CROSS_COMPILE)objdump'
        self._ar = ar or '$(CROSS_COMPILE)ar'
        self._size = size or '$(CROSS_COMPILE)size'
        self._gdb = gdb or '$(CROSS_COMPILE)gdb'
        self._gdbaddr = gdbaddr or 'localhost'
        self._gdbport = gdbport or 3333
        self._tty = tty or '$(firstword $(wildcard /dev/ttyACM* /dev/ttyUSB*))'
        self._baud = baud or 115200

        self._cflags = cflags or []
        self._asmflags = asmflags or []
        self._lflags = lflags or []

        self.decls = outputs.OutputField(self)
        self.rules = outputs.OutputField(self)

    def box(self, box):
        self.pushattrs(
            target=self._target,
            cross_compile=self._cross_compile,
            debug=box.debug,
            lto=box.lto,
            cc=self._cc,
            objcopy=self._objcopy,
            objdump=self._objdump,
            ar=self._ar,
            size=self._size,
            gdb=self._gdb,
            gdbaddr=self._gdbaddr,
            gdbport=self._gdbport,
            tty=self._tty,
            baud=self._baud)

    def default_build_box_prologue(self, box):
        self.decls.append('TARGET         ?= %(target)s',
            target=self._target
                if self._target else
                '%s.elf' % (box.name or 'system'))
        self.decls.append('CROSS_COMPILE  ?= %(cross_compile)s')
        self.decls.append('DEBUG          ?= %(debug)d')
        self.decls.append('LTO            ?= %(lto)d')
        # note we can't use ?= for program names, implicit
        # makefile variables get in the way :(
        self.decls.append('CC             = %(cc)s')
        self.decls.append('OBJCOPY        = %(objcopy)s')
        self.decls.append('OBJDUMP        = %(objdump)s')
        self.decls.append('AR             = %(ar)s')
        self.decls.append('SIZE           = %(size)s')
        self.decls.append('GDB            = %(gdb)s')
        self.decls.append('GDBADDR        ?= %(gdbaddr)s')
        self.decls.append('GDBPORT        ?= %(gdbport)s')
        self.decls.append('TTY            ?= %(tty)s')
        self.decls.append('BAUD           ?= %(baud)s')
        self.decls.append()

        for src in box.srcs:
            self.decls.append('SRC += %(path)s', path=src)
        self.decls.append()

        for inc in box.incs:
            self.decls.append('INC += %(path)s', path=inc)
        self.decls.append()

        for lib in self._libs:
            self.decls.append('LIB += %(path)s', path=lib)
        self.decls.append()

        self.decls.append('LDSCRIPT := $(firstword $(wildcard '
            '$(patsubst %%,%%/*.ld,$(SRC))))')
        self.decls.append()

        self.decls.append('OBJ := $(patsubst %%.c,%%.o,'
            '$(wildcard $(patsubst %%,%%/*.c,$(SRC))))')
        self.decls.append('OBJ += $(patsubst %%.s,%%.o,'
            '$(wildcard $(patsubst %%,%%/*.s,$(SRC))))')
        self.decls.append('OBJ += $(patsubst %%.S,%%.o,'
            '$(wildcard $(patsubst %%,%%/*.S,$(SRC))))')
        self.decls.append('DEP := $(patsubst %%.o,%%.d,$(OBJ))')
        for child in box.boxes:
            path = os.path.relpath(child.path, box.path)
            self.decls.append('BOXES += %(path)s/%(box)s.box',
                box=child.name, path=path)
        self.decls.append()

        out = self.decls.append()
        out.printf('ifneq ($(DEBUG),0)')
        out.printf('override CFLAGS += -DDEBUG')
        out.printf('override CFLAGS += -g')
        out.printf('override CFLAGS += -O0')
        out.printf('else')
        out.printf('override CFLAGS += -DNDEBUG')
        out.printf('override CFLAGS += -Os')
        out.printf('ifneq ($(LTO),0)')
        out.printf('override CFLAGS += -flto')
        out.printf('endif')
        out.printf('endif')
        out.printf('override CFLAGS += -mthumb')
        out.printf('override CFLAGS += -mcpu=cortex-m4')
        out.printf('override CFLAGS += -mfpu=fpv4-sp-d16')
        out.printf('override CFLAGS += -mfloat-abi=softfp')
        out.printf('override CFLAGS += -std=c99')
        out.printf('override CFLAGS += -Wall -Wno-format')
        out.printf('override CFLAGS += -fno-common')
        out.printf('override CFLAGS += -ffunction-sections')
        out.printf('override CFLAGS += -fdata-sections')
        out.printf('override CFLAGS += -ffreestanding')
        out.printf('override CFLAGS += -fno-builtin')
        for k, v in sorted(self._defines.items()):
            out.printf('override CFLAGS += -D%s=%s' % (k, v))
        out.printf('override CFLAGS += $(patsubst %%,-I%%,$(INC))')
        for cflag in self._cflags:
            out.printf('override CFLAGS += %s' % cflag)
        self.decls.append()

        out = self.decls.append()
        out.printf('override ASMFLAGS += $(CFLAGS)')
        for asmflag in self._asmflags:
            out.printf('override ASMFLAGS += %s' % asmflag)
        self.decls.append()

        out = self.decls.append()
        out.printf('override LFLAGS += $(CFLAGS)')
        out.printf('override LFLAGS += -T$(LDSCRIPT)')
        out.printf('override LFLAGS += -Wl,--start-group '
            '$(patsubst %%,-l%%,$(LIB)) -Wl,--end-group')
        out.printf('override LFLAGS += -static')
        out.printf('override LFLAGS += --specs=nano.specs')
        out.printf('override LFLAGS += --specs=nosys.specs')
        out.printf('override LFLAGS += -Wl,--gc-sections')
        out.printf('override LFLAGS += -Wl,-static')
        out.printf('override LFLAGS += -Wl,-z -Wl,muldefs')
        for lflag in self._lflags:
            out.printf('override LFLAGS += %s' % lflag)
        self.decls.append()
        
    def default_build_box(self, box):
        # default rule
        out = self.rules.append(phony=True, doc='default rule')
        out.printf('all build: $(TARGET)')

        # some convenient commands
        out = self.rules.append(phony=True,
            doc="computing size size is a bit complicated as each .elf "
                "includes its boxes, we want independent sizes.")
        out.printf('size: $(TARGET)')
        with out.indent():
            out.writef('$(strip ( $(SIZE) $<')
            with out.indent():
                for child in box.boxes:
                    path = os.path.relpath(child.path, box.path)
                    out.writef(' ;\\\n$(MAKE) -s --no-print-directory '
                        '-C %(path)s size', path=path)
                out.writef(' ) | awk \'\\\n')
                with out.indent():
                    out.writef(
                        'function f(t, d, b, n) {printf \\\n'
                        '    "%%7d %%7d %%7d %%7d %%7x %%s\\n", \\\n'
                        '    t, d, b, t+d+b, t+d+b, n} \\\n'
                        'NR==1 {print} \\\n'
                        'NR==2 {t=$$1; d=$$2; b=$$3; n=$$6} \\\n'
                        'NR>3 && /^([ \\t]+[0-9]+){3,}/ && !/TOTALS/ {'
                        '   l[NR-4]=$$0; t-=$$1+$$2; b-=$$3+$$2;'
                        '   tt+=$$1; td+=$$2; tb+=$$3} \\\n'
                        'END {f(t, d, b, n)} \\\n'
                        'END {for (i in l) print l[i]} \\\n'
                        'END {f(t+tt, d+td, b+tb, "(TOTALS)")}\')')

        out = self.rules.append(phony=True)
        out.printf('debug: $(TARGET)')
        with out.indent():
            out.printf('echo \'$$qRcmd,68616c74#fc\' '
                '| nc -N $(GDBADDR) $(GDBPORT) && echo # halt')
            out.printf('$(strip $(GDB) $< \\\n'
                '    -ex "target remote $(GDBADDR):$(GDBPORT)")')
            out.printf('echo \'$$qRcmd,676f#2c\' '
                '| nc -N $(GDBADDR) $(GDBPORT) && echo # go')

        out = self.rules.append(phony=True)
        out.printf('flash: $(TARGET)')
        with out.indent():
            out.printf('echo \'$$qRcmd,68616c74#fc\' '
                '| nc -N $(GDBADDR) $(GDBPORT) && echo # halt')
            out.printf('$(strip $(GDB) $< \\\n'
                '    -ex "target remote $(GDBADDR):$(GDBPORT)" \\\n'
                '    -ex "load" \\\n'
                '    -ex "monitor reset" \\\n'
                '    -batch)')

        out = self.rules.append(phony=True)
        out.printf('reset:')
        with out.indent():
            out.printf('echo \'$$qRcmd,7265736574#37\' '
                '| nc -N $(GDBADDR) $(GDBPORT) && echo # reset')
            out.printf('echo \'$$qRcmd,676f#2c\' '
                '| nc -N $(GDBADDR) $(GDBPORT) && echo # go')

        out = self.rules.append(phony=True)
        out.printf('cat:')
        with out.indent():
            out.printf('stty -F $(TTY) sane nl $(BAUD)')
            out.printf('cat $(TTY)')

        out = self.rules.append(phony=True)
        out.printf('tags:')
        with out.indent():
            out.writef('$(strip ctags')
            with out.indent():
                out.writef(' \\\n$(wildcard $(patsubst %%,%%/*.c,$(SRC)))')
                out.writef(' \\\n$(wildcard $(patsubst %%,%%/*.s,$(SRC)))')
                out.writef(' \\\n$(wildcard $(patsubst %%,%%/*.S,$(SRC)))')
                out.writef(')')

        for child in box.boxes:
            path = os.path.relpath(child.path, box.path)
            out = self.rules.append(box=child.name, path=path)
            out.printf('.PHONY: $(shell '
                'make -s -C %(path)s %(box)s.box -q || '
                'echo %(path)s/%(box)s.box)')
            out.printf('%(path)s/%(box)s.box:')
            with out.indent():
                out.printf('@echo "' + 6*'='
                    + (' make -C %s ' % out['box']).center(48-2*6, '=')
                    + 6*'=' + '"')
                out.printf('$(MAKE) --no-print-directory -C %(path)s '
                    '%(box)s.box')
                out.printf('@echo "' + 48*'=' + '"')

        # target rule
        out = self.rules.append(doc='target rule')
        out.printf('$(TARGET): $(OBJ) $(BOXES) $(LDSCRIPT)')
        with out.indent():
            out.printf('$(CC) $(OBJ) $(BOXES) $(LFLAGS) -o $@')

        self.rules.append('-include $(DEP)', doc="header dependencies")

        # create boxing rule, to be invoked if embedding an elf is needed
        data_init = None
        if any(section.name == 'data'
                for memory in box.memoryslices
                for section in memory.sections):
            data_init = box.consume('r', 0)
        out = self.rules.append(
            doc="a .box is a .elf stripped, with sections prefixed by "
                "the names of the allocated memory regions")
        out.printf('%%.box: %%.elf' + ' %%.box.data'*(data_init is not None))
        with out.indent():
            out.writef('$(strip $(OBJCOPY) $< $@ \\\n')
            with out.indent():
                out.writef('--strip-all')
                if data_init is not None:
                    out.writef(' \\\n--add-section '
                        '.box.%(box)s.%(memory)s.data=$(word 2,$^)',
                        memory=data_init.name)
                for i, memory in enumerate(box.memoryslices):
                    for j, section in enumerate(memory.sections):
                        out.writef(' \\\n--only-section .%(section)s',
                            section=section.name)
                        out.writef(' \\\n--rename-section .%(section)s='
                            '.box.%(box)s.%(memory)s.%(section)s',
                            memory=memory.name,
                            section=section.name)
                out.writef(')\n')

        out = self.rules.append()
        if data_init is not None:
            out.printf('%%.box.data: %%.elf')
            with out.indent():
                out.printf('$(OBJCOPY) $< $@ -O binary -j .data')

        # other rules
        out = self.rules.append()
        out.printf('%%.bin: %%.elf')
        with out.indent():
            out.printf('$(OBJCOPY) -O binary $< $@')

        out = self.rules.append()
        out.printf('%%.o: %%.c')
        with out.indent():
            out.printf('$(CC) -c -MMD -MP $(CFLAGS) $< -o $@')

        out = self.rules.append()
        out.printf('%%.s: %%.c')
        with out.indent():
            out.printf('$(CC) -S -MMD -MP $(CFLAGS) $< -o $@')

        out = self.rules.append()
        out.printf('%%.o: %%.s')
        with out.indent():
            out.printf('$(CC) -c -MMD -MP $(ASMFLAGS) $< -o $@')

        out = self.rules.append()
        out.printf('%%.o: %%.S')
        with out.indent():
            out.printf('$(CC) -c -MMD -MP $(ASMFLAGS) $< -o $@')

        out = self.rules.append(phony=True)
        out.printf('clean:')
        with out.indent():
            out.printf('rm -f $(TARGET) $(BOXES)')
            out.printf('rm -f $(OBJ)')
            out.printf('rm -f $(DEP)')
            for child in box.boxes:
                path = os.path.relpath(child.path, box.path)
                out.printf('$(MAKE) -C %(path)s clean', path=path)

    def build(self, box):
        self.write('###### BENTO-BOX AUTOGENERATED ######\n')
        self.write('\n')
        if self.decls:
            for decl in self.decls:
                if 'doc' in decl:
                    for line in textwrap.wrap(decl['doc'], width=77):
                        self.write('# %s\n' % line)
                self.write(decl.getvalue().strip())
                self.write('\n')
        for rule in self.rules:
            if 'doc' in rule:
                for line in textwrap.wrap(rule['doc'], width=77):
                    self.write('# %s\n' % line)
            value = rule.getvalue().strip()
            value = re.sub('^    ', '\t', value, flags=re.M)
            if rule.get('phony', False):
                self.write('.PHONY: %s\n' % re.match(
                    r'^([^:]*):', value).group(1))
            self.write(value)
            self.write('\n\n')
            
