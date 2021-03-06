#
# Makefile outputer
# 
# Copyright (c) 2020, Arm Limited. All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause
#
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

LLVM_TRIPLES = co.defaultdict(
    lambda: 'thumbv7em-v7m-none-gnueabi'
)

WAMRC_TRIPLES = co.defaultdict(
    lambda: 'thumb'
)

RUST_TRIPLES = co.defaultdict(
    lambda: 'thumbv7em-none-eabi',
    **{
        'cortex-m33': 'thumbv8m.main-none-eabi',
        'wasm': 'wasm32-unknown-unknown',
    }
)

@outputs.output
class MkOutput(outputs.Output):
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
        parser.add_argument('--asserts', type=bool,
            help='Enables asserts independently of debug mode. Defaults to '
                'true.')
        defineparser = parser.add_set('--define', append=True)
        defineparser.add_argument('define',
            help='Adds custom defines to the Makefile. For example: '
                '--define.ENABLE_BIG=1.')

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

        parser.add_argument('--cargo',
            help='Provide the cargo program for the makefile. This can be '
                '--cargo=cargo if cargo can be found in your path. If not '
                'provided, the generated makefile will error when asked to '
                'compile Rust crates.')
        parser.add_argument('--crates', type=list,
            help='Supply Rust crate directories. This only needs to be the '
                'root library crate as Rust\'s module system automatically '
                'finds dependencies. Defaults to [\'.\'].')

        parser.add_argument('--cargo_flags', type=list,
            help='Add custom Cargo flags.')

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

        parser.add_argument('--wasm_cargo',
            help='Provide the cargo program for the makefile. This can be '
                '--wasm_cargo=cargo if cargo can be found in your path. If not '
                'provided, the generated makefile will error when asked to '
                'compile Rust crates.')
        parser.add_argument('--wasm_crates', type=list,
            help='Supply Rust crate directories. This only needs to be the '
                'root library crate as Rust\'s module system automatically '
                'finds dependencies. Defaults to [\'.\'].')

        parser.add_argument('--wasm_cargo_flags', type=list,
            help='Add custom Cargo flags.')

        parser.add_argument('--awsm',
            help='Provide the aWsm ahead-of-time compiler.')
        parser.add_argument('--llvm_cc',
            help='Provide the LLVM compiler for the makefile. This is '
                'different from --cc as the LLVM compiler must also accept '
                'LLVM bitcode (.bc) files. This is often set to `clang`.')
        parser.add_argument('--llvm_sysroot',
            help='Override the sysroot for LLVM. By default this is found '
                'automatically from the compiler in --cc.')
        parser.add_argument('--llvm_link',
            help='Override the llvm-link program, used to link LLVM bitcode '
                'files. Required for LTO prior to --cc linking.')
        parser.add_argument('--llvm_opt',
            help='Override the llvm-opt program.')
        parser.add_argument('--llvm_dis',
            help='Override the llvm-dis program.')

        parser.add_argument('--llvm_srcs', type=list,
            help='Supply source directories. Defaults to [\'.\'].')
        parser.add_argument('--llvm_incs', type=list,
            help='Supply include directories. Defaults to what\'s '
                'passed to --llvm_srcs.')

        parser.add_argument('--awsm_flags', type=list,
            help='Add custom aWsm flags.')
        parser.add_argument('--llvm_c_flags', type=list,
            help='Add custom LLVM C flags.')

        parser.add_argument('--wamrc',
            help='Provide the Wamr ahead-of-time compiler.')
        parser.add_argument('--wamrc_flags', type=list,
            help='Add custom Wamr compiler flags.')

    def __init__(self, path=None, target=None,
            debug=None, lto=None, asserts=None, define=None,
            cc=None, objcopy=None, objdump=None, ar=None,
            size=None, gdb=None, gdb_addr=None, gdb_port=None,
            tty=None, baud=None,
            cpu=None, fpu=None, isa=None,
            srcs=None, incs=None, libs=None,
            c_flags=None, asm_flags=None, ld_flags=None,
            cargo=None, crates=None,
            cargo_flags=None,
            wasi_sdk=None, wabt=None,
            wasm_cc=None, wasm_sysroot=None, wasm_strip=None,
            wasm_objdump=None, wasm_wasm2wat=None, wasm_wat2wasm=None,
            wasm_cpu=None, wasm_srcs=None, wasm_incs=None, wasm_libs=None,
            wasm_c_flags=None, wasm_ld_flags=None,
            wasm_cargo=None, wasm_crates=None,
            wasm_cargo_flags=None,
            awsm=None, llvm_cc=None, llvm_sysroot=None,
            llvm_link=None, llvm_opt=None, llvm_dis=None,
            llvm_srcs=None, llvm_incs=None,
            awsm_flags=None, llvm_c_flags=None,
            wamrc=None, wamrc_flags=None):
        super().__init__(path)

        self._target = target
        self._debug = debug if debug is not None else False
        self._lto = lto if lto is not None else True
        self._asserts = asserts if asserts is not None else True
        self._defines = co.OrderedDict(sorted(
            (k, getattr(v, 'define', v)) for k, v in define.items()))

        self._cc = cc or '%(gcc_triple)s-gcc'
        self._objcopy = objcopy or '%(gcc_triple)s-objcopy'
        self._objdump = objdump or '%(gcc_triple)s-objdump'
        self._ar = ar or '%(gcc_triple)s-ar'
        self._size = size or '%(gcc_triple)s-size'
        self._gdb = gdb or '%(gcc_triple)s-gdb'
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

        self._cargo = cargo
        self._crates = crates if crates is not None else ['.']

        self._cargo_flags = cargo_flags if cargo_flags is not None else []

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
            os.path.join(wabt, 'bin/wasm2wat')
            if wabt else
            None)
        self._wasm_wat2wasm = (wasm_wat2wasm
            if wasm_wat2wasm else
            os.path.join(wabt, 'bin/wat2wasm')
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

        self._wasm_cargo = wasm_cargo
        self._wasm_crates = wasm_crates if wasm_crates is not None else ['.']

        self._wasm_cargo_flags = (wasm_cargo_flags
            if wasm_cargo_flags is not None else
            [])

        self._awsm = awsm
        self._llvm_cc = llvm_cc
        self._llvm_sysroot = llvm_sysroot or '$(shell $(CC) -print-sysroot)'
        self._llvm_link = llvm_link or 'llvm-link'
        self._llvm_opt = llvm_opt or 'opt'
        self._llvm_dis = llvm_dis or 'llvm-dis'

        self._llvm_srcs = llvm_srcs if llvm_srcs is not None else ['.']
        self._llvm_incs = (llvm_incs
            if llvm_incs is not None else
            self._llvm_srcs)

        self._llvm_srcs = llvm_srcs if llvm_srcs is not None else ['.']
        self._llvm_incs = (llvm_incs
            if llvm_incs is not None else
            self._llvm_srcs)

        self._awsm_flags = awsm_flags if awsm_flags is not None else []
        self._llvm_c_flags = llvm_c_flags if llvm_c_flags is not None else []

        self._wamrc = wamrc
        self._wamrc_flags = wamrc_flags if wamrc_flags is not None else []

        # used to decide what gets emitting into Makefile
        self.no_rust = self._cargo is None
        self.no_wasm = self._wasm_cc is None
        self.no_wasm_rust = self.no_wasm or self._wasm_cargo is None
        self.no_awsm = self._awsm is None
        self.no_llvm = self._llvm_cc is None
        self.no_wamrc = self._wamrc is None

        self.decls = outputs.OutputField(self)
        self.userdecls = outputs.OutputField(self)
        self.rules = outputs.OutputField(self)

    def box(self, box):
        super().box(box)
        self.pushattrs(
            target=self._target,
            TARGET='$(TARGET)'
                if self.no_wasm else
                '$(TARGET:.wasm=.elf)'
                # TODO handle all of this differently,
                # take attribute from box?
                if self.no_wamrc or not (
                    box.runtime == 'wamr' and box.runtime._aot) else
                '$(TARGET:.aot=.elf)',
            debug=self._debug,
            lto=self._lto,
            asserts=self._asserts,
            cc=self._cc,
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
            gcc_triple=GCC_TRIPLES[self._cpu],
            cargo=self._cargo,
            rust_triple=RUST_TRIPLES[self._cpu],
            wasm_cc=self._wasm_cc,
            wasm_sysroot=self._wasm_sysroot,
            wasm_strip=self._wasm_strip,
            wasm_objdump=self._wasm_objdump,
            wasm_wasm2wat=self._wasm_wasm2wat,
            wasm_wat2wasm=self._wasm_wat2wasm,
            wasm_cpu=self._wasm_cpu,
            wasm_cargo=self._wasm_cargo,
            wasm_rust_triple=RUST_TRIPLES['wasm'],
            awsm=self._awsm,
            llvm_cc=self._llvm_cc,
            llvm_sysroot=self._llvm_sysroot,
            llvm_link=self._llvm_link,
            llvm_opt=self._llvm_opt,
            llvm_dis=self._llvm_dis,
            llvm_triple=LLVM_TRIPLES[self._cpu],
            wamrc=self._wamrc,
            wamrc_triple=WAMRC_TRIPLES[self._cpu])

    def build_prologue(self, box):
        out = self.decls.append()
        out.printf('DEBUG            ?= %(debug)d')
        out.printf('LTO              ?= %(lto)d')
        out.printf('ASSERTS          ?= %(asserts)d')
        # note we can't use ?= for program names, implicit
        # makefile variables get in the way :(
        out.printf('CC               = %(cc)s')
        out.printf('OBJCOPY          = %(objcopy)s')
        out.printf('OBJDUMP          = %(objdump)s')
        out.printf('AR               = %(ar)s')
        out.printf('SIZE             = %(size)s')
        out.printf('GDB              = %(gdb)s')
        out.printf('GDBADDR          ?= %(gdb_addr)s')
        out.printf('GDBPORT          ?= %(gdb_port)s')
        out.printf('TTY              ?= %(tty)s')
        out.printf('BAUD             ?= %(baud)s')
        if not self.no_rust:
            out.printf('CARGO            = %(cargo)s')
        if not self.no_wasm:
            out.printf('WASMCC           = %(wasm_cc)s')
            out.printf('WASMSYSROOT      ?= %(wasm_sysroot)s')
            out.printf('WASMSTRIP        = %(wasm_strip)s')
            out.printf('WASMOBJDUMP      = %(wasm_objdump)s')
            out.printf('WASMWASM2WAT     = %(wasm_wasm2wat)s')
            out.printf('WASMWAT2WASM     = %(wasm_wat2wasm)s')
        if not self.no_wasm_rust:
            out.printf('WASMCARGO        = %(wasm_cargo)s')
        if not self.no_awsm:
            out.printf('AWSM             = %(awsm)s')
        if not self.no_llvm:
            out.printf('LLVMCC           = %(llvm_cc)s')
            out.printf('LLVMSYSROOT      ?= %(llvm_sysroot)s')
            out.printf('LLVMLINK         = %(llvm_link)s')
            out.printf('LLVMOPT          = %(llvm_opt)s')
            out.printf('LLVMDIS          = %(llvm_dis)s')
        if not self.no_wamrc:
            out.printf('WAMRC            = %(wamrc)s')

    def build(self, box):
        out = self.decls.append()
        for src in self._srcs:
            out.printf('SRC += %(path)s', path=src)
        for inc in self._incs:
            out.printf('INC += %(path)s', path=inc)
        for lib in self._libs:
            out.printf('LIB += %(path)s', path=lib)
        if not self.no_rust:
            for crate in self._crates:
                out.printf('CRATES += %(path)s', path=crate)
        if not self.no_wasm:
            for src in self._wasm_srcs:
                out.printf('WASMSRC += %(path)s', path=src)
            for inc in self._wasm_incs:
                out.printf('WASMINC += %(path)s', path=inc)
            for lib in self._wasm_libs:
                out.printf('WASMLIB += %(path)s', path=lib)
        if not self.no_wasm_rust:
            for crate in self._wasm_crates:
                out.printf('WASMCRATES += %(path)s', path=crate)
        if not self.no_llvm:
            for src in self._llvm_srcs:
                out.printf('LLVMSRC += %(path)s', path=src)
            for inc in self._llvm_incs:
                out.printf('LLVMINC += %(path)s', path=inc)

        if not self.no_rust:
            out = self.decls.append(doc='find crate libs in one pass')
            out.printf('CRATELIBS := $(foreach crate,$(CRATES),$\\\n'
                '    $(foreach lib,$\\\n'
                '        $(shell $(CARGO) metadata $\\\n'
                '            --manifest-path=$(crate)/Cargo.toml $\\\n'
                '            --format-version=1 --no-deps $\\\n'
                '            | jq -r \'.packages'
                                 '|.[].name'
                                 '|gsub("-";"_")\'),$\\\n'
                '        $(crate)/target/%(rust_triple)s/$\\\n'
                '            $(if $(filter-out 0,$(DEBUG)),debug,release)/$\\\n'
                '            lib$(lib).a))')
        if not self.no_wasm_rust:
            out = self.decls.append(doc='find crate libs in one pass')
            out.printf('WASMCRATELIBS := $(foreach crate,$(WASMCRATES),$\\\n'
                '    $(foreach lib,$\\\n'
                '        $(shell $(WASMCARGO) metadata $\\\n'
                '            --manifest-path=$(crate)/Cargo.toml $\\\n'
                '            --format-version=1 --no-deps $\\\n'
                '            | jq -r \'.packages'
                                 '|.[].name'
                                 '|gsub("-";"_")\'),$\\\n'
                '        $(crate)/target/%(wasm_rust_triple)s/$\\\n'
                '            $(if $(filter-out 0,$(DEBUG)),debug,release)/$\\\n'
                '            lib$(lib).a))')

        out = self.decls.append()
        out.printf('OBJ := $(patsubst %%.c,%%.o,'
            '$(wildcard $(patsubst %%,%%/*.c,$(SRC))))')
        out.printf('OBJ += $(patsubst %%.s,%%.o,'
            '$(wildcard $(patsubst %%,%%/*.s,$(SRC))))')
        out.printf('OBJ += $(patsubst %%.S,%%.o,'
            '$(wildcard $(patsubst %%,%%/*.S,$(SRC))))')
        out.printf('DEP := $(patsubst %%.o,%%.d,$(OBJ))')
        if not self.no_rust:
            out.printf('SRC += $(dir $(CRATELIBS))')
            out.printf('LIB += $(patsubst lib%%.a,%%,$(notdir $(CRATELIBS)))')
        out.printf('LDSCRIPT := $(firstword $(wildcard '
            '$(patsubst %%,%%/*.ld,$(SRC))))')
        if not self.no_wasm:
            out.printf('WASMOBJ := $(patsubst %%.c,%%.wo,'
                '$(wildcard $(patsubst %%,%%/*.c,$(WASMSRC))))')
            out.printf('WASMOBJ += $(patsubst %%.s,%%.wo,'
                '$(wildcard $(patsubst %%,%%/*.s,$(WASMSRC))))')
            out.printf('WASMOBJ += $(patsubst %%.S,%%.wo,'
                '$(wildcard $(patsubst %%,%%/*.S,$(WASMSRC))))')
            out.printf('DEP += $(patsubst %%.wo,%%.d,$(WASMOBJ))')
        if not self.no_wasm_rust:
            out.printf('WASMSRC += $(dir $(WASMCRATELIBS))')
            out.printf('WASMLIB += $(patsubst lib%%.a,%%,'
                '$(notdir $(WASMCRATELIBS)))')
        if not self.no_llvm:
            out.printf('LLVMOBJ := $(patsubst %%.c,%%.bc,'
                '$(wildcard $(patsubst %%,%%/*.c,$(LLVMSRC))))')
            out.printf('LLVMOBJ += $(patsubst %%.s,%%.bc,'
                '$(wildcard $(patsubst %%,%%/*.s,$(LLVMSRC))))')
            out.printf('LLVMOBJ += $(patsubst %%.S,%%.bc,'
                '$(wildcard $(patsubst %%,%%/*.S,$(LLVMSRC))))')
            out.printf('DEP += $(patsubst %%.bc,%%.d,$(LLVMOBJ))')
        for child in box.boxes:
            path = os.path.relpath(child.path, box.path)
            out.printf('BOXES += %(path)s/%(box)s.box',
                box=child.name, path=path)

        out = self.decls.append()
        out.printf('override CFLAGS += -g')
        out.printf('ifneq ($(DEBUG),0)')
        out.printf('override CFLAGS += -O0')
        out.printf('else')
        out.printf('ifeq ($(ASSERTS),0)')
        out.printf('override CFLAGS += -DNDEBUG')
        out.printf('endif')
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
        out.printf('override CFLAGS += -fshort-enums')
        out.printf('override CFLAGS += $(patsubst %%,-I%%,$(INC))')

        if not self.no_rust:
            out = self.decls.append()
            out.printf('override CARGOFLAGS += --target=%(rust_triple)s')
            out.printf('ifeq ($(DEBUG),0)')
            out.printf('override CARGOFLAGS += --release')
            out.printf('endif')

        if not self.no_wasm:
            out = self.decls.append()
            out.printf('ifneq ($(DEBUG),0)')
            out.printf('override WASMCFLAGS += -g')
            out.printf('override WASMCFLAGS += -Oz')
            out.printf('else')
            out.printf('ifeq ($(ASSERTS),0)')
            out.printf('override WASMCFLAGS += -DNDEBUG')
            out.printf('endif')
            out.printf('override WASMCFLAGS += -Oz')
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
            out.printf('override WASMCFLAGS += $(patsubst %%,-I%%,$(WASMINC))')

        if not self.no_wasm_rust:
            out = self.decls.append()
            out.printf('override WASMCARGOFLAGS += '
                '--target=%(wasm_rust_triple)s')
            out.printf('ifeq ($(DEBUG),0)')
            out.printf('override WASMCARGOFLAGS += --release')
            out.printf('endif')

        if not self.no_awsm:
            out = self.decls.append()
            out.printf('override AWSMFLAGS += --target=%(llvm_triple)s')

        if not self.no_llvm:
            out = self.decls.append()
            out.printf('ifneq ($(DEBUG),0)')
            out.printf('# note we need the -always-inline pass otherwise the')
            out.printf('# resulting binary is unusably large')
            out.printf('override LLVMOPTFLAGS += -O1')
            out.printf('else')
            out.printf('override LLVMOPTFLAGS += -Oz')
            out.printf('endif')

            out = self.decls.append()
            out.printf('override LLVMCFLAGS += -g')
            out.printf('ifneq ($(DEBUG),0)')
            out.printf('# note we need the -always-inline pass otherwise the')
            out.printf('# resulting binary is unusably large')
            out.printf('override LLVMCFLAGS += -O1')
            out.printf('else')
            out.printf('ifeq ($(ASSERTS),0)')
            out.printf('override LLVMCFLAGS += -DNDEBUG')
            out.printf('endif')
            out.printf('override LLVMCFLAGS += -Oz')
            out.printf('ifneq ($(LTO),0)')
            out.printf('override LLVMCFLAGS += -flto')
            out.printf('endif')
            out.printf('endif')
            if out.get('isa', False):
                out.printf('override LLVMCFLAGS += -m%(isa)s')
            if out.get('cpu', False):
                out.printf('override LLVMCFLAGS += -mcpu=%(cpu)s')
            if out.get('fpu', False):
                out.printf('override LLVMCFLAGS += -mfpu=%(fpu)s')
                out.printf('override LLVMCFLAGS += -mfloat-abi=softfp')
            out.printf('override LLVMCFLAGS += --target=%(llvm_triple)s')
            out.printf('override LLVMCFLAGS += --sysroot=$(LLVMSYSROOT)')
            out.printf('override LLVMCFLAGS += -I$(LLVMSYSROOT)/include')
            out.printf('override LLVMCFLAGS += -std=c99')
            out.printf('override LLVMCFLAGS += -Wall -Wno-format')
            out.printf('override LLVMCFLAGS += -fno-common')
            out.printf('override LLVMCFLAGS += -ffunction-sections')
            out.printf('override LLVMCFLAGS += -fdata-sections')
            out.printf('override LLVMCFLAGS += -ffreestanding')
            out.printf('override LLVMCFLAGS += -fno-builtin')
            out.printf('override LLVMCFLAGS += -fshort-enums')
            out.printf('override LLVMCFLAGS += $(patsubst %%,-I%%,$(LLVMINC))')

        if not self.no_wamrc:
            out = self.decls.append()
            out.printf('override WAMRCFLAGS += --target=%(wamrc_triple)s')

        out = self.decls.append()
        out.printf('override ASMFLAGS += $(CFLAGS)')

        out = self.decls.append()
        out.printf('override LDFLAGS += $(CFLAGS)')
        out.printf('override LDFLAGS += $(addprefix -T,$(LDSCRIPT))')
        out.printf('override LDFLAGS += $(patsubst %%,-L%%,$(SRC))')
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
            out.printf('override WASMLDFLAGS += $(patsubst %%,-L%%,$(WASMSRC))')
            out.printf('override WASMLDFLAGS += $(patsubst %%,-l%%,$(WASMLIB))')
            out.printf('override WASMLDFLAGS += -Wl,--gc-sections')
            out.printf('override WASMLDFLAGS += -Wl,--no-entry')
            out.printf('override WASMLDFLAGS += -Wl,--allow-undefined')
            out.printf('override WASMLDFLAGS += -Wl,--stack-first')

        # default rule
        self.rules.append('### rules ###')
        out = self.rules.append(phony=True, doc='default rule')
        out.printf('all build: $(TARGET)')

        # some convenient commands
        out = self.rules.append(phony=True,
            doc="computing size size is a bit complicated as each .elf "
                "includes its boxes, we want independent sizes.")
        out.printf('size: %(TARGET)s $(BOXES)')
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
        out.printf('debug: %(TARGET)s')
        with out.indent():
            out.printf('echo \'$$qRcmd,68616c74#fc\' '
                '| nc -N $(GDBADDR) $(GDBPORT) && echo # halt')
            out.printf('$(strip $(GDB) $< \\\n'
                '    -ex "target remote $(GDBADDR):$(GDBPORT)")')
            out.printf('echo \'$$qRcmd,676f#2c\' '
                '| nc -N $(GDBADDR) $(GDBPORT) && echo # go')

        out = self.rules.append(phony=True)
        out.printf('flash: %(TARGET)s')
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
            out.writef('$(strip ctags --totals')
            with out.indent():
                out.writef(' \\\n$(shell find -H $(INC) -name \'*.h\')')
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
        out = self.rules.append(doc="header dependencies")
        out.printf('-include $(DEP)')

        if not self.no_rust:
            out = self.rules.append()
            out.printf('define CRATERULE')
            out.printf('.PHONY: $(crate)')
            out.printf('$(crate):')
            with out.indent():
                out.printf('$(CARGO) build '
                    '--manifest-path=$(crate)/Cargo.toml $(CARGOFLAGS)')
            out.printf('endef')
            out.printf('$(foreach crate,$(CRATES),$(eval $(CRATERULE)))')

        if not self.no_wasm_rust:
            out = self.rules.append()
            out.printf('define WASMCRATERULE')
            out.printf('.PHONY: $(crate)')
            out.printf('$(crate):')
            with out.indent():
                out.printf('$(WASMCARGO) build '
                    '--manifest-path=$(crate)/Cargo.toml $(WASMCARGOFLAGS)')
            out.printf('endef')
            out.printf('$(foreach crate,$(WASMCRATES),'
                '$(eval $(WASMCRATERULE)))')

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
            out.printf('%%.wasm.stripped: %%.wasm')
            with out.indent():
                out.printf('# remove zero data elements, you would expect this')
                out.printf('# from lld but it\'s not currently supported')
                out.printf('$(WASMWASM2WAT) $< -o $@')
                out.printf('sed -i \'s/(data[^"]*"\\(\\\\00\\)*")//g\' $@')
                out.printf('$(WASMWAT2WASM) $@ -o $@')
                out.printf('# and remove symbols')
                out.printf('$(WASMSTRIP) $@')

            # the family of wasm formats expects to know the file size, which
            # when storing images in flash means we need to get a bit hacky
            out = self.rules.append()
            out.printf('%%.prefixed: %%')
            with out.indent():
                out.printf('$(strip python3 -c \'import sys, struct; \\\n'
                    '    d=open(sys.argv[1], "rb").read(); \\\n'
                    '    sys.stdout.buffer.write('
                            'struct.pack("<I", len(d))); \\\n'
                    '    sys.stdout.buffer.write(d);\' $< > $@)')

        if not self.no_llvm:
            out = self.rules.append()
            out.printf('%%.bc: %%.c')
            with out.indent():
                out.printf('$(LLVMCC) -c -emit-llvm '
                    '-MMD -MP $(LLVMCFLAGS) $< -o $@')

            out = self.rules.append()
            out.printf('%%.ll: %%.bc')
            with out.indent():
                out.printf('$(LLVMDIS) $< -o $@')

        out = self.rules.append(phony=True)
        out.printf('clean:')
        with out.indent():
            out.printf('rm -f $(TARGET) $(BOXES)')
            out.printf('rm -f $(OBJ)')
            out.printf('rm -f $(DEP)')
            if not self.no_rust:
                out.printf('$(foreach crate,$(CRATES),'
                    '$(CARGO) clean --manifest-path=$(crate)/Cargo.toml)')
            if not self.no_wasm:
                out.printf('rm -f $(TARGET:.wasm=.elf) $(WASMOBJ)')
            if not self.no_wasm_rust:
                out.printf('$(foreach crate,$(WASMCRATES),'
                    '$(WASMCARGO) clean --manifest-path=$(crate)/Cargo.toml)')
            if not self.no_awsm:
                out.printf('rm -f $(TARGET:.elf=.bc) '
                    '$(TARGET:.elf=.wasm) '
                    '$(TARGET:.elf=.awsm.bc) '
                    '$(TARGET:.elf=.awsm.o)')
            if not self.no_llvm:
                out.printf('rm -f $(LLVMOBJ)')
            if not self.no_wamrc:
                out.printf('rm -f $(TARGET:.aot=.elf) '
                    '$(TARGET:.aot=.wasm)')
            for child in box.boxes:
                path = os.path.relpath(child.path, box.path)
                out.printf('$(MAKE) -C %(path)s clean', path=path)

    def build_epilogue(self, box):
        # we put these at the end so they have precedence
        if self._defines:
            out = self.userdecls.append()
            for k, v in self._defines.items():
                out.printf('override CFLAGS += -D%s=%r' % (k, v))
                if not self.no_wasm:
                    out.printf('override WASMCFLAGS += -D%s=%r' % (k, v))

        if self._c_flags:
            out = self.userdecls.append()
            for flag in self._c_flags:
                out.printf('override CFLAGS += %s' % flag)

        if self._asm_flags:
            out = self.userdecls.append()
            for flag in self._asm_flags:
                out.printf('override ASMFLAGS += %s' % flag)

        if self._ld_flags:
            out = self.userdecls.append()
            for flag in self._ld_flags:
                out.printf('override LDFLAGS += %s' % flag)

        if self._cargo_flags:
            out = self.userdecls.append()
            for flag in self._cargo_flags:
                out.printf('override CARGOFLAGS += %s' % flag)

        if self._awsm_flags:
            out = self.userdecls.append()
            for flag in self._awsm_flags:
                out.printf('override AWSMFLAGS += %s' % flag)

        if self._wasm_c_flags:
            out = self.userdecls.append()
            for flag in self._wasm_c_flags:
                out.printf('override WASMCFLAGS += %s' % flag)

        if self._wasm_ld_flags:
            out = self.userdecls.append()
            for flag in self._wasm_ld_flags:
                out.printf('override WASMLDFLAGS += %s' % flag)

        if self._wasm_cargo_flags:
            out = self.userdecls.append()
            for flag in self._wasm_cargo_flags:
                out.printf('override WASMCARGOFLAGS += %s' % flag)

        if self._llvm_c_flags:
            out = self.userdecls.append()
            for flag in self._llvm_c_flags:
                out.printf('override LLVMCFLAGS += %s' % flag)

        if self._wamrc_flags:
            out = self.userdecls.append()
            for flag in self._wamrc_flags:
                out.printf('override WAMRCFLAGS += %s' % flag)

        if self.userdecls:
            self.userdecls.insert(0, '### user provided flags ###')

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

        if self.userdecls:
            for decl in self.userdecls:
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
