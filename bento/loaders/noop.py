from .. import loaders

@loaders.loader
class NoOpLoader(loaders.Loader):
    """
    A loader that does nothing, allowing execution in
    the specified flash and RAM.
    """
    __argname__ = "noop"
    __arghelp__ = __doc__
    def __init__(self):
        super().__init__()

    def build_parent_c(self, output, parent, box):
        super().build_parent_c(output, parent, box)

        output.decls.append('//// %(box)s loading ////')
        out = output.decls.append()
        out.printf("static int __box_%(box)s_load(void) {")
        with out.indent():
            out.printf("// default loader does nothing")
            out.printf("return 0;")
        out.printf("}")
