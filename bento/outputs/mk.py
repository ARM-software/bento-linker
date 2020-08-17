from .. import outputs
import textwrap
import re
import os
import itertools as it
import collections as co

CPUS = co.defaultdict(
    lambda: 'cortex-m4'
)

FPUS = co.defaultdict(
    lambda: '',
    **{
        'cortex-m4': 'fpv4-sp-d16',
        'cortex-m33': 'fpv5-sp-d16',
    }
)

ISAS = co.defaultdict(
    lambda: 'thumb',
)

GCC_TRIPLES = co.defaultdict(
    lambda: 'arm-none-eabi'
)

RUST_TRIPLES = co.defaultdict(
    lambda: 'thumbv7em-none-eabi',
    **{
        'cortex-m33': 'thumbv8m.main-none-eabi',
    }
)

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
            help='Override the target output for the makefile. Defaults to'
                'runtime specific target.')
        parser.add_argument('--debug', type=bool,
            help='Enables debug mode during compilation. Defaults to false.')
        parser.add_argument('--lto', type=bool,
            help='Enables link-time optimizations during compilation. '
                'Defaults to true.')
        defineparser = parser.add_set('--define', append=True)
        defineparser.add_argument('define',
            help='Adds custom defines to the Makefile. For example: '
                '--define.ENABLE_BIG=1.')

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

        parser.add_argument('--cpu',
            help='CPU to provide to build system. Defaults to cortex-m4.')
        parser.add_argument('--fpu',
            help='FPU to provide to build system. Default based on CPU.')
        parser.add_argument('--isa',
            help='ISA to provide to build system. Default based on CPU.')

        parser.add_argument('--srcs', type=list,
            help='Supply source directories. Defaults to [\'.\'].')
        parser.add_argument('--incs', type=list,
            help='Supply include directories. Defaults to what\'s '
                'passed to --srcs.')
        parser.add_argument('--libs', type=list,
            help='Override libraries. Defaults to '
                '[\'m\', \'c\', \'gcc\', and \'nosys\'].')

        parser.add_argument('--c_flags', type=list,
            help='Add custom C flags.')
        parser.add_argument('--asm_flags', type=list,
            help='Add custom assembly flags.')
        parser.add_argument('--ld_flags', type=list,
            help='Add custom linker flags.')

        parser.add_argument('--wasi_sdk',
            help='Provide path to a WASI SDK build. This will be used to '
                'provide tools for WebAssembly compilation.')
        parser.add_argument('--wabt',
            help='Provide path to a WABT build. This will be used to '
                'provide tools for WebAssembly compilation.')

        parser.add_argument('--wasm_cc',
            help='Override the C compiler for WebAssembly. By default, the '
                'wasi-sdk option will be used to find a C compiler. If '
                'wasi-sdk is not provided, the generated makefile will error '
                'when asked to produce WebAssembly.')
        parser.add_argument('--wasm_sysroot',
            help='Override the sysroot for WebAssembly.')
        parser.add_argument('--wasm_strip',
            help='Override the wasm-strip program for WebAssembly.')
        parser.add_argument('--wasm_objdump',
            help='Override the wasm-objdump program for WebAssembly.')
        parser.add_argument('--wasm_wasm2wat',
            help='Override the wasm2wat program for WebAssembly.')
        parser.add_argument('--wasm_wat2wasm',
            help='Override the wat2wasm program for WebAssembly.')

        parser.add_argument('--wasm_cpu',
            help='WebAssembly CPU to provide to build system. '
                'Defaults to mvp.')

        parser.add_argument('--wasm_srcs', type=list,
            help='Supply source directories. Defaults to [\'.\'].')
        parser.add_argument('--wasm_incs', type=list,
            help='Supply include directories. Defaults to what\'s '
                'passed to --wasm_srcs.')
        parser.add_argument('--wasm_libs', type=list,
            help='Override libraries. Defaults to [].')

        parser.add_argument('--wasm_c_flags', type=list,
            help='Add custom WebAssembly C flags.')
        parser.add_argument('--wasm_ld_flags', type=list,
            help='Add custom WebAssembly linker flags.')

    def __init__(self, path=None, target=None,
            debug=None, lto=None, define=None,
            cc=None, cargo=None, objcopy=None, objdump=None, ar=None,
            size=None, gdb=None, gdb_addr=None, gdb_port=None,
            tty=None, baud=None,
            cpu=None, fpu=None, isa=None,
            srcs=None, incs=None, libs=None,
            c_flags=None, asm_flags=None, ld_flags=None,
            wasi_sdk=None, wabt=None,
            wasm_cc=None, wasm_sysroot=None, wasm_strip=None,
            wasm_objdump=None, wasm_wasm2wat=None, wasm_wat2wasm=None,
            wasm_cpu=None, wasm_srcs=None, wasm_incs=None, wasm_libs=None,
            wasm_c_flags=None, wasm_ld_flags=None):
        super().__init__(path)

        self._target = target
        self._debug = debug if debug is not None else False
        self._lto = lto if lto is not None else True
        self._defines = co.OrderedDict(sorted(
            (k, getattr(v, 'define', v)) for k, v in define.items()))

        self._cc = cc or '%(gcctriple)s-gcc'
        self._cargo = cargo or 'cargo'
        self._objcopy = objcopy or '%(gcctriple)s-objcopy'
        self._objdump = objdump or '%(gcctriple)s-objdump'
        self._ar = ar or '%(gcctriple)s-ar'
        self._size = size or '%(gcctriple)s-size'
        self._gdb = gdb or '%(gcctriple)s-gdb'
        self._gdb_addr = gdb_addr or 'localhost'
        self._gdb_port = gdb_port or 3333
        self._tty = tty or '$(firstword $(wildcard /dev/ttyACM* /dev/ttyUSB*))'
        self._baud = baud or 115200

        self._cpu = cpu if cpu is not None else 'cortex-m4'
        self._fpu = fpu if fpu is not None else FPUS[self._cpu]
        self._isa = isa if isa is not None else ISAS[self._cpu]

        self._srcs = srcs if srcs is not None else ['.']
        self._incs = incs if incs is not None else self._srcs
        self._libs = libs if libs is not None else ['m', 'c', 'gcc', 'nosys']

        self._c_flags = c_flags if c_flags is not None else []
        self._asm_flags = asm_flags if asm_flags is not None else []
        self._ld_flags = ld_flags if ld_flags is not None else []

        self._wasm_cc = (wasm_cc
            if wasm_cc else
            os.path.join(wasi_sdk, 'bin/clang')
            if wasi_sdk else
            None)
        self._wasm_sysroot = (wasm_cc
            if wasm_cc else
            os.path.join(wasi_sdk, 'share/wasi-sysroot')
            if wasi_sdk else
            None)
        self._wasm_strip = (wasm_strip
            if wasm_strip else
            os.path.join(wabt, 'bin/wasm-strip')
            if wabt else
            None)
        self._wasm_objdump = (wasm_objdump
            if wasm_objdump else
            os.path.join(wabt, 'bin/wasm-objdump')
            if wabt else
            None)
        self._wasm_wasm2wat = (wasm_wasm2wat
            if wasm_wasm2wat else
            os.path.join(wabt, 'bin/wasm-wasm2wat')
            if wabt else
            None)
        self._wasm_wat2wasm = (wasm_wat2wasm
            if wasm_wat2wasm else
            os.path.join(wabt, 'bin/wasm-wat2wasm')
            if wabt else
            None)

        self._wasm_cpu = wasm_cpu if wasm_cpu is not None else 'mvp'

        self._wasm_srcs = wasm_srcs if wasm_srcs is not None else ['.']
        self._wasm_incs = (wasm_incs
            if wasm_incs is not None else
            self._wasm_srcs)
        self._wasm_libs = wasm_libs if wasm_libs is not None else []

        self._wasm_c_flags = wasm_c_flags if wasm_c_flags is not None else []
        self._wasm_ld_flags = wasm_ld_flags if wasm_ld_flags is not None else []

        # used to decide what gets emitting into Makefile
        self.no_wasm = self._wasm_cc is None

        self.decls = outputs.OutputField(self)
        self.rules = outputs.OutputField(self)

    def box(self, box):
        super().box(box)
        self.pushattrs(
            target=self._target,
            debug=self._debug,
            lto=self._lto,
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
            baud=self._baud,
            cpu=self._cpu,
            fpu=self._fpu,
            isa=self._isa,
            gcctriple=GCC_TRIPLES[self._cpu],
            rusttriple=RUST_TRIPLES[self._cpu],
            wasm_cc=self._wasm_cc,
            wasm_sysroot=self._wasm_sysroot,
            wasm_strip=self._wasm_strip,
            wasm_objdump=self._wasm_objdump,
            wasm_wasm2wat=self._wasm_wasm2wat,
            wasm_wat2wasm=self._wasm_wat2wasm,
            wasm_cpu=self._wasm_cpu)

    def build_prologue(self, box):
        out = self.decls.append()
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
        if not self.no_wasm:
            out.printf('WASMCC           ?= %(wasm_cc)s')
            out.printf('WASMSYSROOT      ?= %(wasm_sysroot)s')
            out.printf('WASMSTRIP        ?= %(wasm_strip)s')
            out.printf('WASMOBJDUMP      ?= %(wasm_objdump)s')
            out.printf('WASMWASM2WAT     ?= %(wasm_wasm2wat)s')
            out.printf('WASMWAT2WASM     ?= %(wasm_wat2wasm)s')

    def build(self, box):
        out = self.decls.append()
        for src in self._srcs:
            out.printf('SRC += %(path)s', path=src)
        for inc in self._incs:
            out.printf('INC += %(path)s', path=inc)
        for lib in self._libs:
            out.printf('LIB += %(path)s', path=lib)
        if not self.no_wasm:
            for src in self._wasm_srcs:
                out.printf('WASMSRC += %(path)s', path=src)
            for inc in self._wasm_incs:
                out.printf('WASMINC += %(path)s', path=inc)
            for lib in self._wasm_libs:
                out.printf('WASMLIB += %(path)s', path=lib)

        out = self.decls.append()
        out.printf('CARGOTOML2ARCHIVE = $(foreach lib,$\\\n'
            '    $(shell $(CARGO) metadata $\\\n'
            '        --manifest-path=$(1) $\\\n'
            '        --format-version=1 --no-deps $\\\n'
            '        | jq -r \'.packages|.[].name|gsub("-";"_")\'),$\\\n'
            '    $(patsubst %%/Cargo.toml,%%,$(1))/$\\\n'
            '        target/%(rusttriple)s/$\\\n'
            '        $(if $(filter-out 0,$(DEBUG)),debug,release)/$\\\n'
            '        lib$(lib).a)')

        out = self.decls.append()
        out.printf('CARGOTOMLS := $(wildcard '
            '$(patsubst %%,%%/Cargo.toml,$(SRC)))')

        out = self.decls.append()
        out.printf('OBJ := $(patsubst %%.c,%%.o,'
            '$(wildcard $(patsubst %%,%%/*.c,$(SRC))))')
        out.printf('OBJ += $(patsubst %%.s,%%.o,'
            '$(wildcard $(patsubst %%,%%/*.s,$(SRC))))')
        out.printf('OBJ += $(patsubst %%.S,%%.o,'
            '$(wildcard $(patsubst %%,%%/*.S,$(SRC))))')
        out.printf('DEP := $(patsubst %%.o,%%.d,$(OBJ))')
        out.printf('LDSCRIPT := $(firstword $(wildcard '
            '$(patsubst %%,%%/*.ld,$(SRC))))')
        out.printf('ARCHIVES := $(wildcard '
            '$(patsubst %%,%%/lib*.a,$(SRC)))')
        out.printf('ARCHIVES += $(foreach toml,$(CARGOTOMLS),'
            '$(call CARGOTOML2ARCHIVE,$(toml)))')
        out.printf('LIB += $(patsubst lib%%.a,%%,'
            '$(notdir $(ARCHIVES)))')
        for child in box.boxes:
            path = os.path.relpath(child.path, box.path)
            out.printf('BOXES += %(path)s/%(box)s.box',
                box=child.name, path=path)
        if not self.no_wasm:
            out.printf('WASMOBJ := $(patsubst %%.c,%%.wo,'
                '$(wildcard $(patsubst %%,%%/*.c,$(WASMSRC))))')
            out.printf('WASMOBJ += $(patsubst %%.s,%%.wo,'
                '$(wildcard $(patsubst %%,%%/*.s,$(WASMSRC))))')
            out.printf('WASMOBJ += $(patsubst %%.S,%%.wo,'
                '$(wildcard $(patsubst %%,%%/*.S,$(WASMSRC))))')
            out.printf('DEP += $(patsubst %%.wo,%%.d,$(WASMOBJ))')
            out.printf('WASMARCHIVES := $(wildcard '
                '$(patsubst %%,%%/lib*.a,$(WASMSRC)))')
            out.printf('WASMLIB += $(patsubst lib%%.a,%%,'
                '$(notdir $(WASMARCHIVES)))')

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
        if out.get('isa', False):
            out.printf('override CFLAGS += -m%(isa)s')
        if out.get('cpu', False):
            out.printf('override CFLAGS += -mcpu=%(cpu)s')
        if out.get('fpu', False):
            out.printf('override CFLAGS += -mfpu=%(fpu)s')
            out.printf('override CFLAGS += -mfloat-abi=softfp')
        out.printf('override CFLAGS += -std=c99')
        out.printf('override CFLAGS += -Wall -Wno-format')
        out.printf('override CFLAGS += -fno-common')
        out.printf('override CFLAGS += -ffunction-sections')
        out.printf('override CFLAGS += -fdata-sections')
        out.printf('override CFLAGS += -ffreestanding')
        out.printf('override CFLAGS += -fno-builtin')
        out.printf('override CFLAGS += $(patsubst %%,-I%%,$(INC))')
        if not self.no_wasm:
            out.printf('ifneq ($(DEBUG),0)')
            out.printf('override WASMCFLAGS += -DDEBUG')
            out.printf('override WASMCFLAGS += -g')
            out.printf('override WASMCFLAGS += -O0')
            out.printf('else')
            out.printf('override WASMCFLAGS += -DNDEBUG')
            out.printf('override WASMCFLAGS += -Os')
            out.printf('ifneq ($(LTO),0)')
            out.printf('override WASMCFLAGS += -flto')
            out.printf('endif')
            out.printf('endif')
            out.printf('override WASMCFLAGS += --target=wasm32-wasi')
            out.printf('override WASMCFLAGS += --sysroot=$(WASMSYSROOT)')
            if out.get('cpu', False):
                out.printf('override WASMCFLAGS += -mcpu=%(wasm_cpu)s')
            out.printf('override WASMCFLAGS += -fvisibility=hidden')
            out.printf('override WASMCFLAGS += -std=c99')
            out.printf('override WASMCFLAGS += -Wall -Wno-format')
            out.printf('override WASMCFLAGS += -fno-common')
            out.printf('override WASMCFLAGS += -ffunction-sections')
            out.printf('override WASMCFLAGS += -fdata-sections')
            out.printf('override WASMCFLAGS += -ffreestanding')
            out.printf('override WASMCFLAGS += -fno-builtin')
            out.printf('override WASMCFLAGS += $(patsubst %%,-I%%,$(INC))')

        out = self.decls.append()
        out.printf('override CARGOFLAGS += --target=%(rusttriple)s')
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
        if not self.no_wasm:
            out.printf('override WASMLDFLAGS += $(WASMCFLAGS)')
            out.printf('override WASMLDFLAGS += '
                '$(patsubst %%,-L%%,$(dir $(ARCHIVES)))')
            out.printf('override WASMLDFLAGS += '
                '$(patsubst %%,-l%%,$(WASMLIB))')
            out.printf('override WASMLDFLAGS += -Wl,--gc-sections')
            out.printf('override WASMLDFLAGS += -Wl,--no-entry')
            out.printf('override WASMLDFLAGS += -Wl,--allow-undefined')
            out.printf('override WASMLDFLAGS += -Wl,--export-dynamic')
            out.printf('override WASMLDFLAGS += -Wl,--stack-first')

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
                out.writef(' \\\n$(shell find $(INC) -name \'*.h\')')
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
        self.rules.append(doc="header dependencies")
        out.printf('-include $(DEP)')

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

        if not self.no_wasm:
            out = self.rules.append()
            out.printf('%%.wo: %%.c')
            with out.indent():
                out.printf('$(WASMCC) -c -MMD -MP $(WASMCFLAGS) $< -o $@')

            out = self.rules.append()
            out.printf('%%.wo: %%.wat')
            with out.indent():
                out.printf('$(WASMWAT2WASM) $< -o $@')

            out = self.rules.append()
            out.printf('%%.wat: %%.wasm')
            with out.indent():
                out.printf('$(WASMWASM2WAT) $< -o $@')

            out = self.rules.append()
            out.printf('%%.wat: %%.wo')
            with out.indent():
                out.printf('$(WASMWASM2WAT) $< -o $@')

            out = self.rules.append()
            out.printf('%%.wasm.strip: %%.wasm')
            with out.indent():
                out.printf('cp $< $@')
                out.printf('$(WASMSTRIP) $@')

        out = self.rules.append(phony=True)
        out.printf('clean:')
        with out.indent():
            out.printf('rm -f $(TARGET) $(BOXES)')
            out.printf('rm -f $(OBJ)')
            out.printf('rm -f $(DEP)')
            out.printf('$(foreach toml,$(CARGOTOMLS),'
                '$(CARGO) clean --manifest-path=$(toml))')
            if not self.no_wasm:
                out.printf('rm -f $(WASMOBJ)')
            for child in box.boxes:
                path = os.path.relpath(child.path, box.path)
                out.printf('$(MAKE) -C %(path)s clean', path=path)

    def build_epilogue(self, box):
        # we put these at the end so they have precedence
        if any([self._defines, self._c_flags, self._asm_flags, self._ld_flags]):
            self.decls.append('### user provided flags ###')

        if self._defines or self._c_flags:
            out = self.decls.append()
            for k, v in self._defines.items():
                out.printf('override CFLAGS += -D%s=%r' % (k, v))

            for cflag in self._c_flags:
                out.printf('override CFLAGS += %s' % cflag)

        if self._asm_flags:
            out = self.decls.append()
            for asmflag in self._asm_flags:
                out.printf('override ASMFLAGS += %s' % asmflag)

        if self._ld_flags:
            out = self.decls.append()
            for lflag in self._ld_flags:
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
