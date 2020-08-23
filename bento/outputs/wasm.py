from .. import outputs
from ..box import Fn
from ..glue import override
import io
import textwrap
import itertools as it

@outputs.output
class WasmHOutput(outputs.HOutput):
    """
    Name of header file for WebAssembly boxes.
    """
    __argname__ = "wasm_h"
    __arghelp__ = __doc__

    @override(outputs.HOutput)
    def _build_exports(self, box):
        for i, export in enumerate(
                export.prebound() for export in box.exports
                if export.source == box):
            if i == 0:
                self.decls.append('//// box exports ////')
            self.decls.append('%(fn)s;',
                fn=self.repr_fn(export,
                    attrs=['__attribute__((used))', 'extern']),
                doc=export.doc)


@outputs.output
class WasmCOutput(outputs.COutput):
    """
    Name of C file for WebAssembly boxes.
    """
    __argname__ = "wasm_c"
    __arghelp__ = __doc__

