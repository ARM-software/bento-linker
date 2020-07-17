import re
import argparse
import sys
import os
import io
import toml
from argparse import Namespace
import itertools as it

def nsnest(ns):
    """
    Create a "nested namespace" from a normal namespace. This
    uses the '.' character as a separator in namespace keys to
    determine how many namespaces are nested.
    """
    if isinstance(ns, Namespace):
        return Namespace(**nsnest(ns.__dict__))

    ndict = {}
    nested = {}
    for k, v in ns.items():
        if '.' in k:
            scope, name = k.split('.', 1)
            nested.setdefault(scope, {})[name] = v
        else:
            ndict[k] = v
    for k, v in nested.items():
        ndict[k] = nsnest(Namespace(**v))
    return ndict

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
        if k in a and k in b and (
                isinstance(a[k], (Namespace, dict)) and
                isinstance(b[k], (Namespace, dict))):
            ndict[k] = nsmerge(a[k], b[k])
        elif k in b and b[k] is not None:
            ndict[k] = b[k]
        elif k in a and a[k] is not None:
            ndict[k] = a[k]
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
        self._dest = None
        self._hidden = False
        self._fake = False

        # allow forcing underscores in optional arguments
        self._underscore = kwargs.pop('underscore', True)

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
            else:
                nargs.append(arg)
            if hasattr(arg, '__arghelp__'):
                kwargs.setdefault('help', arg.__arghelp__)
        args = nargs

        # default gets in the way of namespace merging, just test
        # for None where needed
        assert kwargs.get('default', None) in {None, argparse.SUPPRESS}, (
            "default in argparse not supported")

        # allow a predicate to test without converting the argument
        if kwargs.get('pred', None) is not None:
            def mktype(rawpred, rawtype):
                def type(x):
                    rawpred(x)
                    return rawtype(x)
                return type
            kwargs['type'] = mktype(
                kwargs.pop('pred'),
                kwargs.pop('type', lambda x: x))

        # some extra special types
        if kwargs.get('type', None) == list:
            def parselist(x):
                m = re.match(r'\[(.*)\]', x.strip())
                if not m:
                    raise ValueError("Not a list %r", x)
                xs = m.group(1).split(',')
                return [re.match(r'(\')?(.*)(?(1)\')', x.strip()).group(2)
                    for x in xs]
            kwargs['type'] = parselist
        elif kwargs.get('type', None) == bool:
            def parsebool(x):
                if x in {'false', 'False', 'no', '0', ''}:
                    return False
                elif x in {'true', 'True', 'yes', '1'}:
                    return True
                else:
                    raise ValueError("I don't recognize this bool "
                        "argument %r" % x)
            kwargs['type'] = parsebool
            kwargs.setdefault('nargs', '?')
            kwargs.setdefault('const', True)
            kwargs.setdefault('metavar', '{true,false}')
        elif kwargs.get('type', None) == int:
            # allow hex ints
            def parseint(x):
                return int(x, 0)
            kwargs['type'] = parseint

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
                        self._dest, nkwargs.get('dest', args[-1][2:]))
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
                        self._dest, nkwargs.get('dest', args[-1]))
                if not (kwargs.get('action', 'store')
                        .startswith('store_')):
                    nkwargs.setdefault('metavar', args[-1].upper())
                self._parent.add_argument('--'+self._name, **nkwargs)
            self._positional.append((args, kwargs))
        return super().add_argument(*args, **kwargs)

    def add_glob(self, cls=None, **kwargs):
        """
        Make all following arguments hidden, instead show a glob (*) with
        summarizing help text. Useful when the number of arguments is long.
        """
        if hasattr(cls, '__arghelp__'):
            kwargs.setdefault('help', cls.__arghelp__)

        self.add_argument('--*', **{**kwargs, 'fake': True})

        self._hidden = True

        if hasattr(cls, '__argparse__'):
            cls.__argparse__(self, **kwargs)

        return self
        

    def add_nestedparser(self, arg, cls=None, **kwargs):
        """
        Add a nested parser, this is different than a subparser in that the
        nested parser in namespaced with long-form optional arguments instead of
        provided a new command.
        """
        # check for special __argparse__ classes
        if not isinstance(arg, str):
            cls = arg
            arg = '--'+cls.__argname__
        if hasattr(cls, '__arghelp__'):
            kwargs.setdefault('help', cls.__arghelp__)

        # we only support long-form names currently
        assert arg.startswith('--')
        name = arg[2:]
        dest = kwargs.get('dest', name)

        # create nested parser
        nested = ArgumentParser()
        # don't actually feed parent if we're globbing
        if not kwargs.get('glob', False):
            nested._parent = self
        nested._name = name
        nested._dest = dest
        nested._hidden = kwargs.get('hidden', False)
        nested._fake = kwargs.get('fake', False)

        if kwargs.get('glob', False):
            # real arg to parse glob
            self.add_argument('--%s.GLOB' % name,
                dest='%s.!GLOB' % dest,
                nargs='?', const=True, hidden=True)
            # fake arg to show in help
            self.add_argument('--%s.*' % name,
                fake=True, metavar='',
                help=kwargs.get('help', None))

        if hasattr(cls, '__argparse__'):
            cls.__argparse__(nested, name=name, **kwargs)

        return nested

    def add_set(self, arg, cls=None, **kwargs):
        """
        Create a nested parser that can capture a set of same-type objects.
        """
        # check for special __argparse__ classes
        if not isinstance(arg, str):
            cls = arg
            arg = '--'+cls.__argname__
        if hasattr(cls, '__arghelp__'):
            kwargs.setdefault('help', cls.__arghelp__)

        # we only support long-form names currently
        assert arg.startswith('--')
        name = arg[2:]
        dest = kwargs.get('dest', name)
        metavar = kwargs.get('metavar', name.upper())
        depth = kwargs.get('depth', 1)
        assert metavar.count('.') == depth-1

        class SetParser(ArgumentParser):
            def add_argument(self, *args, **kwargs):
                args, kwargs = self._post_add_argument(*args, **kwargs)

                if any(arg.startswith('--') for arg in args):
                    if self._parent:
                        # generate nested argument in parent
                        nargs = [re.sub('--(.*)', r'--%s.%s.\1' % (
                                self._name, metavar),
                                arg)
                            for arg in args
                            if arg.startswith('--')]
                        nkwargs = kwargs.copy()
                        if nkwargs.get('dest', True):
                            nkwargs['dest'] = '%s.%s.%s' % (
                                self._dest,
                                '.'.join(it.repeat('!SET', depth)),
                                nkwargs.get('dest', args[-1][2:]))
                        if not (kwargs.get('action', 'store')
                                .startswith('store_')):
                            nkwargs.setdefault('metavar',
                                nkwargs.get('dest', args[-1][2:])
                                    .split('.')[-1].upper())
                        self._parent.add_argument(*nargs, **nkwargs)
                    self._optional.append((args, kwargs))
                else:
                    if self._parent:
                        # generate nested argument in parent
                        nargs = ['--%s.%s' % (
                            self._name,
                            metavar)]
                        nkwargs = kwargs.copy()
                        if nkwargs.get('dest', True):
                            nkwargs['dest'] = '%s.%s.%s' % (
                                self._dest,
                                '.'.join(it.repeat('!SET', depth)),
                                nkwargs.get('dest', args[-1]))
                        if not (kwargs.get('action', 'store')
                                .startswith('store_')):
                            nkwargs.setdefault('metavar',
                                nkwargs.get('dest', args[-1][2:])
                                    .split('.')[-1].upper())
                        self._parent.add_argument(*nargs, **nkwargs)
                    self._positional.append((args, kwargs))

                return super(ArgumentParser, self).add_argument(*args, **kwargs)

        nested = SetParser()
        # don't actually feed parent if we're globbing
        if not kwargs.get('glob', False):
            nested._parent = self
        nested._name = name
        nested._dest = dest
        nested._hidden = kwargs.get('hidden', False)
        nested._fake = kwargs.get('fake', False)

        if kwargs.get('glob', False):
            # real arg to parse glob
            self.add_argument('--%s.%s.GLOB' % (name, metavar),
                dest='%s.!SET.!GLOB' % dest,
                nargs='?', const=True, hidden=True)
            if kwargs.get('action', None) == 'append':
                # enable appending?
                self.add_argument('--%s.%s' % (name, metavar),
                    dest='%s.!SET.!STORE' % dest,
                    action='store_true', hidden=True)

            # fake arg to show in help
            self.add_argument('--%s.%s.*' % (name, metavar),
                fake=True, metavar='',
                help=kwargs.get('help', None))

        # Default set entry creation
        if kwargs.get('action', None) == 'append':
            nkwargs = kwargs.copy()
            nkwargs['action'] = 'store_true'
            nkwargs.pop('glob', None)
            nkwargs.pop('metavar', None)
            nkwargs.pop('depth', None)
            nested.add_argument('!STORE', **nkwargs)

        if hasattr(cls, '__argparse__'):
            cls.__argparse__(nested, name=name, **kwargs)

        return nested

    def parse_known_args(self, args=None, ns=None):
        if args is None:
            args = sys.argv[1:]

        # force underscores?
        if self._underscore:
            nargs = []
            for arg in args:
                if arg.startswith('--'):
                    a, *b = arg[2:].split('=')
                    a = a.replace('-', '_')
                    arg = '--%s=%s' % (a, ''.join(b))
                nargs.append(arg)
            args = nargs

        # parse explicit args first
        ns, args = super().parse_known_args(args, ns)

        # parse out sets, this is a bit complicated
        set_prefixes = []
        nns = Namespace()
        for oargs, okwargs in self._optional:
            if not okwargs.get('dest', False):
                continue
            om = re.search(r'(!GLOB|!SET)([\w-]*)\b', okwargs['dest'])
            if om:
                dest = okwargs['dest'][:om.start()-1]
                for oarg in oargs:
                    pattern = '\.'.join(
                        r'([\.\w-]+)'
                        if rule.startswith('!GLOB') else
                        r'([\w-]+)'
                        if rule == '!SET' else
                        part
                        for part, rule in zip(
                            oarg.split('.'),
                            it.chain(
                                okwargs['dest'].split('.'),
                                it.repeat(''))))

                    for arg in args:
                        m = re.match('^%s(?:=|$)' % pattern, arg)
                        if m:
                            # ugh, is an ordered set too much to ask for?
                            set_prefixes.append((
                                arg[:m.start(1)],
                                m.group(1),
                                okwargs['dest']))

                            # add default empty set
                            #ns = ns or Namespace()
                            ns.__dict__ = {
                                k: v for k, v in ns.__dict__.items()
                                if not k.startswith(dest)}
                ns.__dict__.setdefault(dest,
                    {} if om.group(1) == '!SET' else Namespace())

        # delete fake args and merge sets
        ns.__dict__ = {
            k: v for k, v in ns.__dict__.items()
            if k and '!' not in k}

        ns = nsnest(ns)

        # create temporary parsers to extract known args
        for prefix, m, dest in set_prefixes:
            tempparser = ArgumentParser(allow_abbrev=False, add_help=False)
            for oargs, okwargs in self._optional:
                if okwargs.get('dest', '').startswith(prefix[2:]+'!'):
                    nargs = [re.sub(
                        r'(?<=^%s)(?:[\w-]+\b)' % re.escape(prefix),
                        m, oarg, 1)
                        for oarg in oargs]
                    nkwargs = okwargs.copy()
                    nkwargs['dest'] = re.sub(
                        r'![\w-]+\b',
                        m, nkwargs['dest'], 1)

                    try:
                        tempparser.add_argument(*nargs, **nkwargs)
                    except argparse.ArgumentError:
                        pass

            nns, args = tempparser.parse_known_args(args, Namespace())

            # turn sets into python dicts, stopping on first rule
            # since later rules get handled by recursive descent
            def nsdict(ns, path):
                if not path:
                    return ns
                elif path[0] == '!SET':
                    return ns.__dict__ if isinstance(ns, Namespace) else ns
                elif path[0] == '!GLOB':
                    return ns
                else:
                    return Namespace(**{k: nsdict(v, path[1:])
                        for k, v in ns.__dict__.items()})
            nns = nsdict(nns, dest.split('.'))

            ns = nsmerge(nns, ns)

        return ns, args

    def parse_dict(self, dict_, prefix=None):
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
                elif v is None:
                    pass
                elif v is True:
                    args.append('--%s=true' % '.'.join(prefix + [k]))
                else:
                    args.append('--%s=%s' % ('.'.join(prefix + [k]), v))

            return args

        # build arguments
        args = buildargs([], dict_)

        stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            # parse the arguments
            return self.parse_args(args)
        except SystemExit:
            if prefix:
                lines = sys.stderr.getvalue().splitlines()
                for line in lines[:-1]:
                    print(line, file=stderr)
                print("%s: error: in %s:" % (
                    os.path.basename(sys.argv[0]), prefix.rstrip('.')),
                    file=stderr)
                print(lines[-1], file=stderr)
            else:
                stderr.write(sys.stderr.getvalue())
            raise
        finally:
            sys.stderr = stderr

    def parse_toml(self, path, prefix=None):
        """
        Convenience method for applying parse_dict to a toml file.
        """
        try:
            return self.parse_dict(toml.load(path), prefix=prefix)
        except SystemExit:
            print("%s: error: while parsing %r" % (
                os.path.basename(sys.argv[0]), path),
                file=sys.stderr)
            raise

