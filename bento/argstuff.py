
import re
import argparse
import sys
import os
import toml
from argparse import Namespace
import itertools as it

def nsmerge(a, b):
    """
    Merge two Namespaces or dicts recursively. Note this doesn't work
    with argparse defaults.
    """
    if isinstance(a, Namespace) and isinstance(b, Namespace):
        return Namespace(**nsmerge(a.__dict__, b.__dict__))
    elif isinstance(a, Namespace):
        a = a.__dict__
    elif isinstance(b, Namespace):
        b = b.__dict__

    ndict = {}
    for k in set(a) | set(b):
        if (k in a and k in b and (
                isinstance(a[k], Namespace) or
                isinstance(b[k], dict))):
            ndict[k] = nsmerge(a[k], b[k])
        elif k in a and a[k] is not None:
            ndict[k] = a[k]
        elif k in b and b[k] is not None:
            ndict[k] = b[k]
        else:
            ndict[k] = None
    return ndict

# This class exists to intercept add_argument calls and remember them.
class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        self._optional = []
        self._positional = []
        self._parent = None
        self._name = None
        self._hidden = False
        self._fake = False

        # things get confusing with abbrevs
        kwargs.setdefault('allow_abbrev', False)
        return super().__init__(*args, **kwargs)

    def _post_add_argument(self, *args, **kwargs):
        # Check for __argparse__ classes, note there's no
        # nested parser to actually invoke
        nargs = []
        for arg in args:
            if not isinstance(arg, str):
                nargs.append('--'+arg.__argname__)
                if hasattr(arg, '__arghelp__'):
                    kwargs.setdefault('help', arg.__arghelp__)
            else:
                nargs.append(arg)
        args = nargs

        # allow a predicate to test without converting the argument
        if 'pred' in kwargs:
            def mktype(rawpred, rawtype):
                def type(x):
                    rawpred(x)
                    return rawtype(x)
                return type
            kwargs['type'] = mktype(
                kwargs.pop('pred'),
                kwargs.pop('type', lambda x: x))

        # enable help=argparse.SUPPRESS but in a more flexible way
        if kwargs.pop('hidden', False) or self._hidden:
            kwargs['help'] = argparse.SUPPRESS

        # enable fake arguments for better help text
        if kwargs.pop('fake', False) or self._fake:
            args = [arg for arg in args if arg.startswith('--')]
            kwargs['dest'] = ''

        return args, kwargs

    def add_argument(self, *args, **kwargs):
        args, kwargs = self._post_add_argument(*args, **kwargs)

        if any(arg.startswith('--') for arg in args):
            if self._parent:
                # Generate nested argument in parent
                nargs = [re.sub('--(.*)', r'--%s.\1' % self._name, arg)
                    for arg in args
                    if arg.startswith('--')]
                nkwargs = kwargs.copy()
                if nkwargs.get('dest', True):
                    nkwargs['dest'] = '%s.%s' % (
                        self._name, nkwargs.get('dest', args[-1][2:]))
                if not (kwargs.get('action', 'store')
                        .startswith('store_')):
                    nkwargs.setdefault('metavar',
                        args[-1][2:].split('.')[-1].upper())
                self._parent.add_argument(*nargs, **nkwargs)
            self._optional.append((args, kwargs))
        else:
            if self._parent:
                # Generate nested argument in parent
                nkwargs = kwargs.copy()
                if nkwargs.get('dest', True):
                    nkwargs['dest'] = '%s.%s' % (
                        self._name, nkwargs.get('dest', args[-1]))
                if not (kwargs.get('action', 'store')
                        .startswith('store_')):
                    nkwargs.setdefault('metavar', args[-1].upper())
                self._parent.add_argument('--'+self._name, **nkwargs)
            self._positional.append((args, kwargs))
        return super().add_argument(*args, **kwargs)

    def add_nestedparser(self, arg, cls=None, **kwargs):
        """
        Add a nested parser, this is different than a subparser in that the
        nested parser in namespaced with long-form optional arguments instead of
        provided a new command.
        """
        # Check for special __argparse__ classes
        if not isinstance(arg, str):
            cls = arg
            arg = '--'+cls.__argname__
            if hasattr(cls, '__arghelp__'):
                kwargs.setdefault('help', cls.__arghelp__)

        # We only support long-form names currently
        assert arg.startswith('--')
        name = arg[2:]

        # Create nested parser
        nested = ArgumentParser()
        nested._parent = self
        nested._name = name
        nested._hidden = kwargs.get('hidden', False)
        nested._fake = kwargs.get('fake', False)

        if hasattr(cls, '__argparse__'):
            cls.__argparse__(nested, name=name, **kwargs)

        return nested

    def add_set(self, arg, cls=None, **kwargs):
        """
        Create a nested parser that can capture a set of same-type objects.
        """
        # Check for special __argparse__ classes
        if not isinstance(arg, str):
            cls = arg
            arg = '--'+cls.__argname__
            if hasattr(cls, '__arghelp__'):
                kwargs.setdefault('help', cls.__arghelp__)

        # We only support long-form names currently
        assert arg.startswith('--')
        name = arg[2:]
        recursive = (kwargs.get('recursive', False)
            and not kwargs.get('fake', False))
        metavar = kwargs.get('metavar', name.upper())

        class SetParser(ArgumentParser):
            def add_argument(self, *args, **kwargs):
                args, kwargs = self._post_add_argument(*args, **kwargs)

                if any(arg.startswith('--') for arg in args):
                    if self._parent:
                        # Generate nested argument in parent
                        nargs = [re.sub('--(.*)', r'--%s.%s.\1' % (
                                self._name, metavar),
                                arg)
                            for arg in args
                            if arg.startswith('--')]
                        nkwargs = kwargs.copy()
                        if nkwargs.get('dest', True):
                            nkwargs['dest'] = '%s.%s.%s' % (
                                self._name,
                                '__REC%s' % self._name
                                if recursive else
                                '__SET',
                                nkwargs.get('dest', args[-1][2:]))
                        if not (kwargs.get('action', 'store')
                                .startswith('store_')):
                            nkwargs.setdefault('metavar', metavar)
                        self._parent.add_argument(*nargs, **nkwargs)
                    self._optional.append((args, kwargs))
                else:
                    if self._parent:
                        # Generate nested argument in parent
                        nargs = ['--%s.%s' % (
                            self._name,
                            metavar)]
                        nkwargs = kwargs.copy()
                        if nkwargs.get('dest', True):
                            nkwargs['dest'] = '%s.%s.%s' % (
                                self._name,
                                '__REC%s' % self._name
                                if recursive else
                                '__SET',
                                nkwargs.get('dest', args[-1]))
                        if not (kwargs.get('action', 'store')
                                .startswith('store_')):
                            nkwargs.setdefault('metavar', metavar)
                        self._parent.add_argument(*nargs, **nkwargs)
                    self._positional.append((args, kwargs))

                return super(ArgumentParser, self).add_argument(*args, **kwargs)

        nested = SetParser()
        nested._parent = self
        nested._name = name
        nested._hidden = kwargs.get('hidden', False)
        nested._fake = kwargs.get('fake', False)

        # Default set entry creation
        if kwargs.get('action', None) == 'append':
            nkwargs = kwargs.copy()
            nkwargs['action'] = 'store_true'
            nkwargs.pop('recursive', None)
            nkwargs.pop('metavar', None)
            hidden = nested._hidden
            if nkwargs.pop('hidden') == 'append_only':
                nested._hidden = False
            nested.add_argument('__STORE', **nkwargs)
            nested._hidden = hidden

        if hasattr(cls, '__argparse__'):
            cls.__argparse__(nested, name=name, **kwargs)

        return nested

    def parse_known_args(self, args=None, ns=None):
        if args is None:
            args = sys.argv[1:]

        # first parse out sets, this is a bit complicated
        set_prefixes = set()
        for oargs, okwargs in self._optional:
            om = re.search(r'\b(__REC|__SET)([\w-]*)\b',
                okwargs.get('dest', ''))
            if om:
                for oarg in oargs:
                    pattern = '.'.join(
                        r'([\w-]+)(?:\.(%s)\.[\w-]+)*' % rule[len('__REC'):]
                        if rule.startswith('__REC') else
                        r'([\w-]+)()'
                        if rule == '__SET' else part
                        for part, rule in zip(
                            oarg.split('.'),
                            it.chain(
                                okwargs['dest'].split('.'),
                                it.repeat(''))))

                    for arg in args:
                        m = re.match(pattern, arg)
                        if m:
                            set_prefixes.add((
                                arg[:m.start(1)],
                                m.group(1),
                                m.group(2)))

                            # need default empty recursive set?
                            if om.group(1) == '__REC':
                                ns.__dict__['%s.%s.%s' % (
                                    okwargs['dest'][:om.start()-1],
                                    m.group(1),
                                    om.group(2))] = {}

                # add default empty set
                ns = ns or Namespace()
                ns.__dict__[okwargs['dest'][:om.start()-1]] = {}

        # create temporary parsers to extract known args
        sets = []
        for prefix, m, suffix in set_prefixes:
            tempparser = ArgumentParser(allow_abbrev=False, add_help=False)
            for oargs, okwargs in self._optional:
                if (any(oarg.startswith(prefix) for oarg in oargs)
                        and okwargs.get('dest', True)):
                    nargs = [re.sub(
                        r'(?<=^%s)[\w-]+\b' % re.escape(prefix),
                        m, oarg, 1)
                        for oarg in oargs]
                    nkwargs = okwargs.copy()
                    nkwargs['dest'] = re.sub(
                        r'(?<=^%s)[\w-]+\b' % re.escape(prefix[2:]),
                        m, nkwargs['dest'], 1)
                    tempparser.add_argument(*nargs, **nkwargs)
                    if suffix:
                        nargs = [re.sub(
                            r'(?<=^%s)[\w-]+\b' % re.escape(prefix),
                            '.'.join([m, suffix, suffix.upper()]),
                            oarg, 1)
                            for oarg in oargs]
                        nkwargs = okwargs.copy()
                        nkwargs['dest'] = re.sub(
                            r'(?<=^%s)[\w-]+\b' % re.escape(prefix[2:]),
                            '.'.join([m, suffix, '__REC'+suffix]),
                            nkwargs['dest'], 1)
                        tempparser.add_argument(*nargs, **nkwargs)

            nns, args = tempparser.parse_known_args(args, Namespace())

            # turn sets into python dicts
            def nsdict(ns, path):
                if not path:
                    return ns
                elif path[0] == '__DICT':
                    return {k: nsdict(v, path[1:])
                        for k, v in ns.__dict__.items()}
                else:
                    return Namespace(**{k: nsdict(v, path[1:])
                        for k, v in ns.__dict__.items()})

            sets.append(nsdict(nns, (prefix+'__DICT').split('.')))

        # parse!
        ns, args = super().parse_known_args(args, ns)

        # delete fake args and merge sets
        ns.__dict__ = {
            k: v for k, v in ns.__dict__.items()
            if not re.search(r'\b__', k)}

        # create nested namespaces
        def nsnest(ns):
            ndict = {}
            nested = {}
            for k, v in ns.__dict__.items():
                if '.' in k:
                    scope, name = k.split('.', 1)
                    nested.setdefault(scope, {})[name] = v
                else:
                    ndict[k] = v
            for k, v in nested.items():
                ndict[k] = nsnest(Namespace(**v))
            return Namespace(**ndict)

        ns = nsnest(ns)

        for nns in sets:
            ns = nsmerge(ns, nns)

        return ns, args

    def parse_dict(self, dict_):
        """
        Apply the argument parser to a dictionary or namespace, sanitizing and
        applying the same type rules that would be applied on the command line.
        """
        def buildargs(prefix, dict_):
            if isinstance(dict_, Namespace):
                dict_ = dict_.__dict__

            args = []
            for k, v in dict_.items():
                if isinstance(v, dict) or isinstance(v, Namespace):
                    args.extend(buildargs(prefix + [k], v))
                else:
                    args.append('--%s=%s' % ('.'.join(prefix + [k]), v))

            return args

        args = buildargs([], dict_)
        return self.parse_args(args)

    def parse_toml(self, path):
        """
        Convenience method for applying parse_dict to a toml file.
        """
        try:
            return self.parse_dict(toml.load(path))
        except SystemExit:
            print("%s: error: while parsing %r" % (
                os.path.basename(sys.argv[0]), path), file=sys.stderr)
            raise

