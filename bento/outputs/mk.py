from .. import outputs
import textwrap
import re
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

        parser.add_argument('--srcs', type=list,
            help='Override source directories. Defaults to \'.\'.')
        parser.add_argument('--incs', type=list,
            help='Override Include directories. Defaults to '
                'source directories.')
        parser.add_argument('--libs', type=list,
            help='Override libraries. Defaults to m, c, gcc, and nosys.')

        defineparser = parser.add_set('--defines',
            append=True, metavar='DEFINE')
        defineparser.add_argument('define',
            help='Add preprocessor defines to the build.')

        parser.add_argument('--target',
            help='Override the target output (name.elf) for the makefile.')
        parser.add_argument('--cross_compile',
            help='Override the compiler triplet (arm-none-eabi-) '
                'for the makefile.')
        parser.add_argument('--debug',
            help='Enable/disable debugging.')
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
            help='Override individual C flags.')
        parser.add_argument('--asmflags', type=list,
            help='Override individual assembly flags.')
        parser.add_argument('--lflags', type=list,
            help='Override individual linker flags.')

    def __init__(self, path=None,
            srcs=None, incs=None, libs=None, defines={},
            target=None, cross_compile=None, debug=None,
            cc=None, objcopy=None, objdump=None, ar=None,
            size=None, gdb=None, gdbaddr=None, gdbport=None,
            tty=None, baud=None,
            cflags=None, asmflags=None, lflags=None):
        super().__init__(path)
        self._srcs = srcs or ['.']
        self._incs = incs or self._srcs
        self._libs = libs or ['m', 'c', 'gcc', 'nosys']
        self._defines = co.OrderedDict(sorted(
            (k, getattr(v, 'define', v)) for k, v in defines.items()))

        self._target = target
        self._cross_compile = cross_compile or 'arm-none-eabi-'
        self._debug = debug or False
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
        self.pushattrs(
            target=self._target,
            cross_compile=self._cross_compile,
            debug=self._debug,
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

        self._cflags = cflags
        self._asmflags = asmflags
        self._lflags = lflags

        self.decls = outputs.OutputField(self)
        self.rules = outputs.OutputField(self)

    def default_build_box_prologue(self, box):
        # TODO this is kinda a weird one
        self.decls.append('TARGET         ?= %(target)s',
            target=self._target
                if self._target else
                '%s.elf' % (box.name or 'sys'))
        self.decls.append('CROSS_COMPILE  ?= %(cross_compile)s')
        self.decls.append('DEBUG          ?= %(debug)d')
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

        for src in self._srcs:
            self.decls.append('SRC += %(path)s', path=src)
        self.decls.append()

        for inc in self._incs:
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
        for child in box.boxes:
            self.decls.append('OBJ += %(box)s.o', box=child.name)
        
        self.decls.append('DEP := $(patsubst %%.o,%%.d,$(OBJ))')
        self.decls.append()

        out = self.decls.append()
        if self._cflags is not None:
            for cflag in self._cflags:
                out.printf('override CFLAGS += %s' % cflag)
        else:
            out.printf('ifneq ($(DEBUG),0)')
            # TODO?
            #out.printf('override CFLAGS += -DDEBUG')
            out.printf('override CFLAGS += -g')
            out.printf('override CFLAGS += -O0')
            out.printf('else')
            # TODO?
            #out.printf('override CFLAGS += -DNDEBUG')
            out.printf('override CFLAGS += -Os')
            out.printf('endif')
            out.printf('override CFLAGS += -mthumb')
            out.printf('override CFLAGS += -mcpu=cortex-m4')
            out.printf('override CFLAGS += -mfpu=fpv4-sp-d16')
            out.printf('override CFLAGS += -mfloat-abi=softfp')
            out.printf('override CFLAGS += -std=c99')
            out.printf('override CFLAGS += -Wall -Wno-format')
            out.printf('override CFLAGS += -fno-common') # TODO hm
            out.printf('override CFLAGS += -ffunction-sections')
            out.printf('override CFLAGS += -fdata-sections')
            out.printf('override CFLAGS += -ffreestanding')
            out.printf('override CFLAGS += -fno-builtin')
        for k, v in sorted(self._defines.items()):
            out.printf('override CFLAGS += -D%s=%s' % (k, v))
        out.printf('override CFLAGS += $(patsubst %%,-I%%,$(INC))')
        self.decls.append()

        out = self.decls.append()
        if self._asmflags is not None:
            for asmflag in self._asmflags:
                out.printf('override ASMFLAGS += %s' % asmflag)
        else:
            out.printf('override ASMFLAGS += $(CFLAGS)')
        self.decls.append()

        out = self.decls.append()
        if self._lflags is not None:
            for lflag in self._lflags:
                out.printf('override LFLAGS += %s' % lflag)
        else:
            out.printf('override LFLAGS += $(CFLAGS)')
        out.printf('override LFLAGS += -T$(LDSCRIPT)')
        out.printf('override LFLAGS += -Wl,--start-group '
            '$(patsubst %%,-l%%,$(LIB)) -Wl,--end-group')
        out.printf('override LFLAGS += -static')
        out.printf('override LFLAGS += --specs=nano.specs')
        out.printf('override LFLAGS += --specs=nosys.specs')
        out.printf('override LFLAGS += -Wl,--gc-sections')
        out.printf('override LFLAGS += -Wl,-static')
        out.printf('override LFLAGS += -Wl,-z -Wl,muldefs') # TODO hm space?
        self.decls.append()
        
    def default_build_box(self, box):
        # default rule
        out = self.rules.append(phony=True, doc='default rule')
        out.printf('all build: $(TARGET)')

        # some convenient commands
        out = self.rules.append(phony=True)
        out.printf('size: $(TARGET)')
        with out.indent():
            out.printf('$(SIZE) $<')

        out = self.rules.append(phony=True)
        out.printf('debug: $(TARGET)')
        with out.indent():
            out.printf('echo \'$$qRcmd,68616c74#fc\' '
                '| nc -N $(GDBADDR) $(GDBPORT) && echo # halt')
            out.printf('$(GDB) $< \\\n'
                '    -ex "target remote $(GDBADDR):$(GDBPORT)"')
            out.printf('echo \'$$qRcmd,676f#2c\' '
                '| nc -N $(GDBADDR) $(GDBPORT) && echo # go')

        out = self.rules.append(phony=True)
        out.printf('flash: $(TARGET)')
        with out.indent():
            out.printf('echo \'$$qRcmd,68616c74#fc\' '
                '| nc -N $(GDBADDR) $(GDBPORT) && echo # halt')
            out.printf('$(GDB) $< \\\n'
                '    -ex "target remote $(GDBADDR):$(GDBPORT)" \\\n'
                '    -ex "load" \\\n'
                '    -ex "monitor reset" \\\n'
                '    -batch')

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
            # TODO hm, this could actually be smarter (use SRC)
            out.printf('ctags $$(find -regex \'.*\.\(h\|c\)\')')

        for child in box.boxes:
            out = self.rules.append(box=child.name, path=child.path)
            out.printf('.PHONY: $(shell '
                'make -s -C %(path)s %(box)s.bin -q || '
                'echo %(path)s/%(box)s.bin)')
            out.printf('%(path)s/%(box)s.bin:')
            with out.indent():
                out.printf('@echo "' + 6*'='
                    + (' make -C %s ' % out['box']).center(48-2*6, '=')
                    + 6*'=' + '"')
                out.printf('$(MAKE) --no-print-directory -C %(path)s '
                    '%(box)s.bin')
                out.printf('@echo "' + 48*'=' + '"')
            out.printf('%(box)s.o: %(path)s/%(box)s.bin')
            with out.indent():
                # Hm, we've lost memory info, grab first memory?
                # TODO there may be a better way to do this, use child's elf?
                memory = child.memories[0]
                out.printf('$(OBJCOPY) $< $@ \\\n'
                    '    -I binary \\\n'
                    '    -O elf32-littlearm \\\n'
                    '    -B arm \\\n'
                    '    --rename-section .data=.box.%(box)s.%(memory)s'
                        ',alloc,load,readonly,data,contents',
                    memory=memory.name)

        self.rules.append('-include $(DEP)')

        out = self.rules.append()
        out.printf('$(TARGET): $(OBJ) $(LDSCRIPT)')
        with out.indent():
            out.printf('$(CC) $(OBJ) $(LFLAGS) -o $@')

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
            out.printf('rm -f $(TARGET)')
            out.printf('rm -f $(OBJ)')
            out.printf('rm -f $(DEP)')
            for child in box.boxes:
                out.printf('$(MAKE) -C %(path)s clean', path=child.path)

    def build(self, box):
        self.write('###### BENTO-BOX AUTOGENERATED ######\n')
        self.write('\n')
        if self.decls:
            for decl in self.decls:
                if 'doc' in decl:
                    for line in textwrap.wrap(decl['doc'], width=78):
                        self.write('# %s\n' % line)
                self.write(decl.getvalue().strip())
                self.write('\n')
        for rule in self.rules:
            if 'doc' in rule:
                for line in textwrap.wrap(rule['doc'], width=78):
                    self.write('# %s\n' % line)
            value = rule.getvalue().strip()
            value = re.sub('^    ', '\t', value, flags=re.M)
            if rule.get('phony', False):
                self.write('.PHONY: %s\n' % re.match(
                    r'^([^:]*):', value).group(1))
            self.write(value)
            self.write('\n\n')
            
