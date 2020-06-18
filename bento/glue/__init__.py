import itertools as it


def Inherit(methods):
    """
    Allow mixins across explicit methods.
    """
    if isinstance(methods, str):
        methods = [methods]

    class Inherit:
        def inherit(self, cls):
            if not hasattr(self, '_inherits'):
                self._inherits = []
            self._inherits.append(cls)

        def inherit_all(self, classes):
            if not hasattr(self, '_inherits'):
                self._inherits = []
            self._inherits.extend(classes)

    def mkmethod(method):
        def inherit(self, *args, **kwargs):
            res = None
            for cls in getattr(self, '_inherits', []):
                if hasattr(cls, method):
                    res = getattr(cls, method)(*args, **kwargs)
            return res
        return inherit

    for method in methods:
        setattr(Inherit, method, mkmethod(method))

    return Inherit


try:
    from ..outputs import OUTPUTS
    class Glue(Inherit(
            ['%s%s%s%s' % (op, level, output, order)
            for op, level, output, order in it.product(
                ['box', 'build'],
                ['_root', '_muxer', '_parent', ''],
                ['_'+Output.__argname__ for Output in OUTPUTS.values()] + [''],
                ['_prologue', '', '_epilogue'])])):
        def __init__(self):
            super().__init__()
            self.name = self.__argname__

        def __eq__(self, other):
            if isinstance(other, Glue):
                return self.name == other.name
            else:
                return self.name == other

        def __lt__(self, other):
            if isinstance(other, Glue):
                return self.name < other.name
            else:
                return self.name < other

except ImportError:
    pass

