#
# WebAssembly outputer
# 
# Copyright (c) 2020, Arm Limited. All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause
#
from .. import outputs
from ..box import Fn
from ..glue import override
import io
import textwrap
import itertools as it


# These basically only exist to allow specialization in glue/runtimes

@outputs.output
class WasmHOutput(outputs.HOutput):
    """
    Name of header file for WebAssembly boxes.
    """
    __argname__ = "wasm_h"
    __arghelp__ = __doc__

@outputs.output
class WasmCOutput(outputs.COutput):
    """
    Name of C file for WebAssembly boxes.
    """
    __argname__ = "wasm_c"
    __arghelp__ = __doc__

@outputs.output
class WasmRustLibOutput(outputs.RustLibOutput):
    """
    Path of Rust file to place the generated bento-box library
    for WebAssembly boxes.
    """
    __argname__ = "wasm_rust_lib"
    __arghelp__ = __doc__
