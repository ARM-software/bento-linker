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
        super().__argparse__(parser, **kwargs)

        parser.add_argument('--target',
            help='Override the target output (name.elf) for the makefile.')
        parser.add_argument('--cc',
            help='Override the C compiler for the makefile.')
        parser.add_argument('--cargo',
            help='Override the cargo program for the makefile.')
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
        parser.add_argument('--gdb_addr',
            help='Override the gdb addr (localhost) for the makefile.')
        parser.add_argument('--gdb_port',
            help='Override the gdb port (3333) for the makefile.')
        parser.add_argument('--tty',
            help='Override the tty file (/dev/tty*) for the makefile.')
        parser.add_argument('--baud',
            help='Override the baud rate (115200) for the makefile.')

        parser.add_argument('--libs', type=list,
            help='Override libraries. Defaults to '
                '[\'m\', \'c\', \'gcc\', and \'nosys\'].')

        parser.add_argument('--c_flags', type=list,
            help='Add custom C flags.')
        parser.add_argument('--asm_flags', type=list,
            help='Add custom assembly flags.')
        parser.add_argument('--l_flags', type=list,
            help='Add custom linker flags.')

    def __init__(self, path=None, target=None,
            cc=None, cargo=None, objcopy=None, objdump=None, ar=None,
            size=None, gdb=None, gdb_addr=None, gdb_port=None,
            tty=None, baud=None,
            libs=None, c_flags=None, asm_flags=None, l_flags=None):
        super().__init__(path)

        self._target = target
        self._cc = cc or 'arm-none-eabi-gcc'
        self._cargo = cargo or 'cargo'
        self._objcopy = objcopy or 'arm-none-eabi-objcopy'
        self._objdump = objdump or 'arm-none-eabi-objdump'
        self._ar = ar or 'arm-none-eabi-ar'
        self._size = size or 'arm-none-eabi-size'
        self._gdb = gdb or 'arm-none-eabi-gdb'
        self._gdb_addr = gdb_addr or 'localhost'
        self._gdb_port = gdb_port or 3333
        self._tty = tty or '$(firstword $(wildcard /dev/ttyACM* /dev/ttyUSB*))'
        self._baud = baud or 115200

        self._libs = libs or ['m', 'c', 'gcc', 'nosys']

        self._c_flags = c_flags or []
        self._asm_flags = asm_flags or []
        self._l_flags = l_flags or []

        self.decls = outputs.OutputField(self)
        self.rules = outputs.OutputField(self)

    def box(self, box):
        super().box(box)
        self.pushattrs(
            target=self._target,
            debug=box.debug,
            lto=box.lto,
            cc=self._cc,
            cargo=self._cargo,
            objcopy=self._objcopy,
            objdump=self._objdump,
            ar=self._ar,
            size=self._size,
            gdb=self._gdb,
            gdb_addr=self._gdb_addr,
            gdb_port=self._gdb_port,
            tty=self._tty,
            baud=self._baud)

    def build_prologue(self, box):
        out = self.decls.append()
        out.printf('TARGET           ?= %(target)s',
            target=self._target
                if self._target else
                '%s.elf' % (box.name or 'sys'))
        out.printf('DEBUG            ?= %(debug)d')
        out.printf('LTO              ?= %(lto)d')
        # note we can't use ?= for program names, implicit
        # makefile variables get in the way :(
        out.printf('CC               = %(cc)s')
        out.printf('CARGO            = %(cargo)s')
        out.printf('OBJCOPY          = %(objcopy)s')
        out.printf('OBJDUMP          = %(objdump)s')
        out.printf('AR               = %(ar)s')
        out.printf('SIZE             = %(size)s')
        out.printf('GDB              = %(gdb)s')
        out.printf('GDBADDR          ?= %(gdb_addr)s')
        out.printf('GDBPORT          ?= %(gdb_port)s')
        out.printf('TTY              ?= %(tty)s')
        out.printf('BAUD             ?= %(baud)s')

    def build(self, box):
        out = self.decls.append()
        for src in box.srcs:
            out.printf('SRC += %(path)s', path=src)

        out = self.decls.append()
        for inc in box.incs:
            out.printf('INC += %(path)s', path=inc)

        out = self.decls.append()
        for lib in self._libs:
            out.printf('LIB += %(path)s', path=lib)

        out = self.decls.append()
        out.printf('CARGOTOML2ARCHIVE = $(foreach lib,$\\\n'
            '    $(shell $(CARGO) metadata $\\\n'
            '        --manifest-path=$(1) $\\\n'
            '        --format-version=1 --no-deps $\\\n'
            '        | jq -r \'.packages|.[].name|gsub("-";"_")\'),$\\\n'
            '    $(patsubst %%/Cargo.toml,%%,$(1))/$\\\n'
            '        target/thumbv7em-none-eabi/$\\\n'
            '        $(if $(filter-out 0,$(DEBUG)),debug,release)/$\\\n'
            '        lib$(lib).a)')

        out = self.decls.append()
        out.printf('LDSCRIPT := $(firstword $(wildcard '
            '$(patsubst %%,%%/*.ld,$(SRC))))')
        out.printf('CARGOTOMLS := $(wildcard '
            '$(patsubst %%,%%/Cargo.toml,$(SRC)))')
        out.printf('ARCHIVES := $(wildcard '
            '$(patsubst %%,%%/lib*.a,$(SRC)))')

        out = self.decls.append()
        out.printf('ARCHIVES += $(foreach toml,$(CARGOTOMLS),'
            '$(call CARGOTOML2ARCHIVE,$(toml)))')
        out.printf('LIB += $(patsubst lib%%.a,%%,$(notdir $(ARCHIVES)))')

        out = self.decls.append()
        out.printf('OBJ := $(patsubst %%.c,%%.o,'
            '$(wildcard $(patsubst %%,%%/*.c,$(SRC))))')
        out.printf('OBJ += $(patsubst %%.s,%%.o,'
            '$(wildcard $(patsubst %%,%%/*.s,$(SRC))))')
        out.printf('OBJ += $(patsubst %%.S,%%.o,'
            '$(wildcard $(patsubst %%,%%/*.S,$(SRC))))')
        out.printf('DEP := $(patsubst %%.o,%%.d,$(OBJ))')
        for child in box.boxes:
            path = os.path.relpath(child.path, box.path)
            out.printf('BOXES += %(path)s/%(box)s.box',
                box=child.name, path=path)

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
        out.printf('override CFLAGS += $(patsubst %%,-I%%,$(INC))')

        out = self.decls.append()
        out.printf('override CARGOFLAGS += --target=thumbv7em-none-eabi')
        out.printf('ifeq ($(DEBUG),0)')
        out.printf('override CARGOFLAGS += --release')
        out.printf('endif')

        out = self.decls.append()
        out.printf('override ASMFLAGS += $(CFLAGS)')

        out = self.decls.append()
        out.printf('override LDFLAGS += $(CFLAGS)')
        out.printf('override LDFLAGS += -T$(LDSCRIPT)')
        out.printf('override LDFLAGS += $(patsubst %%,-L%%,$(dir $(ARCHIVES)))')
        out.printf('override LDFLAGS += -Wl,--start-group '
            '$(patsubst %%,-l%%,$(LIB)) -Wl,--end-group')
        out.printf('override LDFLAGS += -static')
        out.printf('override LDFLAGS += --specs=nano.specs')
        out.printf('override LDFLAGS += --specs=nosys.specs')
        out.printf('override LDFLAGS += -Wl,--gc-sections')
        out.printf('override LDFLAGS += -Wl,-static')
        out.printf('override LDFLAGS += -Wl,-z,muldefs')
        
        # default rule
        self.rules.append('### rules ###')
        out = self.rules.append(phony=True, doc='default rule')
        out.printf('all build: $(TARGET)')

        # some convenient commands
        out = self.rules.append(phony=True,
            doc="computing size size is a bit complicated as each .elf "
                "includes its boxes, we want independent sizes.")
        out.printf('size: $(TARGET) $(BOXES)')
        with out.indent():
            if not box.boxes:
                # simpler form if we have no boxes
                out.printf('$(SIZE) $<')
            else:
                out.writef('$(strip ( $(SIZE) $^')
                with out.indent():
                    for child in box.boxes:
                        path = os.path.relpath(child.path, box.path)
                        out.writef(' ; \\\n$(MAKE) -s --no-print-directory '
                            '-C %(path)s size', path=path)
                    out.writef(' ) | awk \'\\\n')
                    with out.indent():
                        out.writef(
                            'function f(t, d, b, n) { \\\n'
                            '    printf "%%7d %%7d %%7d %%7d %%7x %%s\\n", \\\n'
                            '    t, d, b, t+d+b, t+d+b, n} \\\n'
                            'NR==1 {print} \\\n'
                            'NR==2 {t=$$1; d=$$2; b=$$3; n=$$6} \\\n'
                            'NR>=3 && NR<%(n)d {bt+=$$1} \\\n'
                            'NR>=%(n)d && '
                                '/^([ \\t]+[0-9]+){3,}/ && !/TOTALS/ { \\\n'
                            '    l[NR-%(n)d]=$$0; bd+=$$2; bb+=$$3} \\\n'
                            'END {f(t-bt, d, b, n)} \\\n'
                            'END {for (i in l) print l[i]} \\\n'
                            'END {f(t, d, b+bd+bb, "(TOTALS)")}\')',
                            n=3+len(box.boxes))

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

        # other rules
        self.rules.append('-include $(DEP)', doc="header dependencies")

        out = self.rules.append()
        out.printf('define CARGORULE')
        out.printf('.PHONY: $(toml)')
        out.printf('$(call CARGOTOML2ARCHIVE,$(toml)): $(toml)')
        with out.indent():
            out.printf('$(CARGO) build --manifest-path=$$< $(CARGOFLAGS)')
        out.printf('endef')
        out.printf('$(foreach toml,$(CARGOTOMLS),$(eval $(CARGORULE)))')

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
            out.printf('$(foreach toml,$(CARGOTOMLS),'
                '$(CARGO) clean --manifest-path=$(toml))')
            for child in box.boxes:
                path = os.path.relpath(child.path, box.path)
                out.printf('$(MAKE) -C %(path)s clean', path=path)

    def build_epilogue(self, box):
        # we put these at the end so they have precedence
        if any([box.defines, self._c_flags, self._asm_flags, self._l_flags]):
            self.decls.append('### user provided flags ###')

        if box.defines or self._c_flags:
            out = self.decls.append()
            for k, v in box.defines.items():
                out.printf('override CFLAGS += -D%s=%s' % (k, v))

            for cflag in self._c_flags:
                out.printf('override CFLAGS += %s' % cflag)

        if self._asm_flags:
            out = self.decls.append()
            for asmflag in self._asm_flags:
                out.printf('override ASMFLAGS += %s' % asmflag)

        if self._l_flags:
            out = self.decls.append()
            for lflag in self._l_flags:
                out.printf('override LDFLAGS += %s' % lflag)

    def getvalue(self):
        self.seek(0)
        self.printf('###### BENTO-BOX AUTOGENERATED ######')
        self.printf('')

        if self.decls:
            for decl in self.decls:
                if 'doc' in decl:
                    for line in textwrap.wrap(decl['doc'], width=78-2):
                        self.print('# %s' % line)
                self.print(decl.getvalue().strip())
                self.print()

        for rule in self.rules:
            if 'doc' in rule:
                for line in textwrap.wrap(rule['doc'], width=78-2):
                    self.print('# %s' % line)
            value = rule.getvalue().strip()
            value = re.sub('^    ', '\t', value, flags=re.M)
            if rule.get('phony', False):
                self.print('.PHONY: %s' % re.match(
                    r'^([^:]*):', value).group(1))
            self.print(value)
            self.print()

        return super().getvalue()
