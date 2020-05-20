import os
import builtins
import abc
import collections as c
import itertools as it
import string
import io
import re

OUTPUTS = {'box': c.OrderedDict(), 'sys': c.OrderedDict()}
def output(target):
    def output(cls):
        assert cls.__argname__ not in OUTPUTS[target]
        OUTPUTS[target][cls.__argname__] = cls
        return cls
    return output

#def cond(f):
#    """ Create conditional function for output apply methods """
#    def cond(self, *args, **kwargs):
#        if self:
#            return f(*args, **kwargs)
#    return cond 

# TODO enable exclusive inheritance between StringIO and file?
class OutputBlob_(io.StringIO):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self._attrs = []
        self._needindent = True
        self.pushattrs(**kwargs)

    def writef(self, fmt, **kwargs):
        fmt = fmt % self.attrs(**kwargs)
        for c in fmt:
            if c == '\n':
                self._needindent = True
            else:
                if self._needindent:
                    self._needindent = False
                    super().write(self.get('indent', 0)*' ')
            self.write(c)

#    def _parsekwarg(self, attr):
#        for rule in [
#                lambda: attr(self),
#                lambda: attr(),
#                lambda: attr % self.attrs()]:
#            try:
#                return rule()
#            except TypeError:
#                continue
#        else:
#            return attr
#
#    def _parsekwargs(self, attrs):
#        return {k: self._parsekwarg(v) for k, v in attrs.items()}

    def pushattrs(self, **kwargs):
#        kwargs = {k: v % self.attrs()
#            if isinstance(v, str) else v
#            for k, v in kwargs.items()}
        #self._attrs.append(self._parsekwargs(kwargs))
        # TODO add fallback for uppercase?
        self._attrs.append(kwargs)

        class context:
            def __enter__(_):
                return self
            def __exit__(*_):
                self.popattrs()
        return context()

    def popattrs(self):
        return self._attrs.pop()

    def pushindent(self, indent=4):
        return self.pushattrs(indent=self.get('indent', 0) + indent)

    def popindent(self):
        assert set(self._attrs[-1].keys()) == {'indent'}
        return self.popattrs()['indent']

    def _expand(self, k, v):
        with self.pushattrs(**{k: None}):
            for rule in [lambda: v(self), lambda: v()]:
                try:
                    return rule()
                except TypeError:
                    continue
            else:
#               try:
                if isinstance(v, str) and re.search(r'%(?!%)', v):
                    return v % self.attrs()
                else:
                    return v
#                except KeyError:
#                    # avoid combinatorial explosion
#                    return v.replace('%', '%%')
#                except TypeError:
#                    return v
#                except:
#                    raise
#
#        for rule in [lambda: v(self), lambda: v()]:
#            try:
#                with self.pushattrs(**{k: None}):
#                    return rule()
#            except TypeError:
#                continue
#        else:
#            if isinstance(v, str) and '%' in v:
#                return v % self.attrs(**{**kwargs, k: None})
#            else:
#                return v
#
    def _expandall(self, attrs):
        expanded = {}
        for k, v in attrs.items():
            if v is None:
                continue
            expanded[k] = self._expand(k, v)
            if k.upper() not in expanded and isinstance(expanded[k], str):
                expanded[k.upper()] = expanded[k].upper()
        return expanded

    def __getitem__(self, key):
#        # try fast lookup first
#        for a in reversed(self._attrs):
#            if key in a:
#                return self._expand(key, a[key])
#
#        # TODO maybe don't do this?
#        # TODO wow, this is EXPENSIVE
#        return self.attrs()[key]
#        # TODO handle UPPER CASE????

        for a in reversed(self._attrs):
            if key in a:
                return self._expand(key, a[key])

        for a in reversed(self._attrs):
            a = {k.upper(): v for k, v in a.items()}
            if key in a:
                return self._expand(key, a[key]).upper()

        raise KeyError(key)

    def __contains__(self, key):
        try:
            self[key]
            return True
        except KeyError:
            return False

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def attrs(self, **kwargs):
#        kwargs = {k: v % self.attrs()
#            if isinstance(v, str) else v
#            for k, v in kwargs.items()}
        #kwargs = self._parsekwargs(kwargs)
        attrs = {}
        for a in self._attrs:
            attrs.update(a)
        attrs.update(kwargs)
        return self._expandall(attrs)
        #attrs.update(self._parsekwargs(kwargs))
        #return {k: v for k, v in attrs.items() if v is not None}

    def __repr__(self):
        return super(object, self).__repr__()


class OutputField_(list):
    def __init__(self, parent=None, rules={}, **kwargs):
        super().__init__()
        self._parent = parent
        self._rules = rules
        self._attrs = kwargs

    def insert(self, _i, _fmt=None, **kwargs):
        if isinstance(_fmt, OutputBlob_):
            outf = _fmt
        else:
#            #outf = OutputBlob_(**self._parent.attrs({**self._attrs, **kwargs}))
#            #outf = OutputBlob_(**self._parent.attrs(**kwargs))
#            outf = OutputBlob_(**self._parent.attrs())
#            # TODO is this correct for handling lambdas in kwargs?
#            # TODO HMMMM
#            if kwargs:
#                outf.pushattrs(**kwargs)
#            if self._attrs:
#                outf.pushattrs(**self._attrs)

            outf = OutputBlob_(**{
                **self._parent.attrs(),
                **self._attrs,
                **kwargs})

#            ruleattrs = {}
#            for attr, rule in self._rules.items():
#                if isinstance(attr, str):
#                    ruleattrs[attr] = rule(outf)
#            if ruleattrs:
#                outf.pushattrs(**ruleattrs)

            for type, rule in self._rules.items():
                if isinstance(_fmt, type):
                    rule(outf, _fmt)
                    break
            else:
                if _fmt is not None:
                    outf.writef(_fmt)

        super().insert(_i, outf)
        return outf

    def append(self, _fmt=None, **kwargs):
        return self.insert(len(self), _fmt, **kwargs)

    def extend(self, iterable):
        for x in iterable:
            self.append(x)

    def __repr__(self):
        return super(object, self).__repr__()

class Output_(OutputBlob_):
    """An optional output that a runtime can generate."""
    __argname__ = "unnamed_output"
    __arghelp__ = __doc__

    def __init__(self, path=None):
        super().__init__()
        self.name = self.__argname__ # TODO need type?
        self.path = path
        self.prologues = c.OrderedDict()
        self.epilogues = c.OrderedDict()

    def __lt__(self, other):
        return self.name < other.name

    def box(self, box):
        self.pushattrs(
            name=self.name,
            path=self.path,
            box=box.name if box.isbox() else None)

    def build(self, box):
        for build, *args in self.epilogues.values():
            build(self, *args)

#    def box(self, box):
#        """
#        Configure output with specified box. This should add any
#        box-specific attributes.
#        """
#        # TODO always have name?
#        #if box.name:
#        if getattr(box, 'name', None):
#            self.pushattrs(box=box.name, BOX=box.name.upper())



#    def build(self, outf):
#        """
#        Build the output into the specified output file.
#        """
#        outf.write(super().getvalue())
#
#    def getvalue(self):
#        # reimplemented to allow subclasses to only override build
#        super().seek(0)
#        super().truncate(0)
#        self.build(super(OutputBlob_, self))
#        return super().getvalue()
#
#
#        outf = io.StringIO()
#        self.build(outf)
#        return outf.getvalue()

#class Output(abc.ABC):
#    """An optional output that a runtime can generate."""
#    __argname__ = "output"
#    __arghelp__ = __doc__
#
#    def __init__(self, sys, box, path):
#        self.path = path
#        # some common spec entries
#        f = {'path': path}
#        if box is not None:
#            f.update({'box': box.name, 'BOX': box.name.upper()})
#        self._format = [f]
#        super().__init__()
#
#    def format(self, **kwargs):
#        self._format[-1].update(kwargs)
#
#    def mkformat(self, **kwargs):
#        format = {}
#        for f in self._format:
#            format.update(f)
#        format.update(kwargs)
#        return format
#
#    def mkfield(self, **kwargs):
#        return OutputField(**self.mkformat(**kwargs))
#
#    def pushformat(self, **kwargs):
#        self._format.append(kwargs)
#
#    def popformat(self):
#        return self._format.pop()
#
#    @abc.abstractmethod
#    def build(self, outf):
#        """Build the output after being passed to the needed runtimes."""
#
#class OutputField(io.StringIO):
#    def __init__(self, *args, **kwargs):
#        self._format = kwargs
#        super().__init__(*args)
#
#    def write(self, fmt, **kwargs):
#        super().write(fmt % {**kwargs, **self._format})

# Output class imports
# These must be imported here, since they depend on the above utilities
from .header import HeaderGlueOutput_
from .jumptable import CGlueOutput_
from .linkerscript import LDScriptOutput_, PartialLDScriptOutput_
