
import re
import argparse
import sys
import os
import toml
from argparse import Namespace

def merge(a, b):
    """
    Merge two Namespaces or dicts recursively. Note this doesn't work
    with argparse defaults.
    """
    if isinstance(a, Namespace):
        return Namespace(**merge(a.__dict__, b.__dict__))

    ndict = {}
    for k in set(a) | set(b):
        if (k in a and k in b and
                (isinstance(a[k], Namespace) or isinstance(b[k], dict))):
            ndict[k] = merge(a[k], b[k])
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
        # TODO rm these?
        self._optional = []
        self._positional = []
        #self._nested__ = {}
        #self._nested = {}
        #self._sets = {}
        self._parent = None
        self._name = None

        # this gets confusing with abbrevs
        kwargs.setdefault('allow_abbrev', False)
        return super().__init__(*args, **kwargs)

    def add_argument(self, *args, **kwargs):
        if any(arg.startswith('--') for arg in args):
            if self._parent:
                # Generate nested argument in parent
                nargs = [re.sub('--(.*)', r'--%s.\1' % self._name[2:], arg)
                    for arg in args
                    if arg.startswith('--')]
                nkwargs = kwargs.copy()
                nkwargs['dest'] = '%s.%s' % (
                    self._name[2:], nkwargs.get('dest', args[-1][2:]))
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
                nkwargs['dest'] = '%s.%s' % (
                    self._name[2:], nkwargs.get('dest', args[-1]))
                if not (kwargs.get('action', 'store')
                        .startswith('store_')):
                    nkwargs.setdefault('metavar', args[-1].upper())
                self._parent.add_argument(self._name, **nkwargs)
            self._positional.append((args, kwargs))
        return super(ArgumentParser, self).add_argument(*args, **kwargs)

    def add_nestedparser(self, name, **kwargs):
        """
        Add a nested parser, this is different than a subparser in that the
        nested parser in namespaced with long-form optional arguments instead of
        provided a new command.
        """
        # We only support long-form names currently
        assert name.startswith('--')

        # Create nested parser
        nested = ArgumentParser()
        nested._parent = self
        nested._name = name
        #self._nested[name] = nested # TODO need this?

        return nested

    def add_set(self, name, **kwargs):
        """
        Create a nested parser that can capture a set of same-type objects.
        """
        assert name.startswith('--')
        class SetParser(ArgumentParser):
            def add_argument(self, *args, **kwargs):
                if any(arg.startswith('--') for arg in args):
                    if self._parent:
                        # Generate nested argument in parent
                        nargs = [re.sub('--(.*)', r'--%s.%s.\1' % (
                                self._name[2:], self._name[2:].upper()), arg)
                            for arg in args
                            if arg.startswith('--')]
                        nkwargs = kwargs.copy()
                        nkwargs['dest'] = '%s.%s.%s' % (
                            self._name[2:], self._name[2:].upper(),
                            nkwargs.get('dest', args[-1][2:]))
                        if not (kwargs.get('action', 'store')
                                .startswith('store_')):
                            nkwargs.setdefault('metavar',
                                args[-1][2:].split('.')[-1].upper())
                        self._parent.add_argument(*nargs, **nkwargs)
                    self._optional.append((args, kwargs))
                else:
                    if self._parent:
                        # Generate nested argument in parent
                        nargs = ['--%s.%s' % (
                            self._name[2:], self._name[2:].upper())]
                        nkwargs = kwargs.copy()
                        nkwargs['dest'] = '%s.%s.%s' % (
                            self._name[2:], self._name[2:].upper(),
                            nkwargs.get('dest', args[-1]))
                        if not (kwargs.get('action', 'store')
                                .startswith('store_')):
                            nkwargs.setdefault('metavar', args[-1].upper())
                        self._parent.add_argument(*nargs, **nkwargs)
                    self._positional.append((args, kwargs))
                return super(ArgumentParser, self).add_argument(*args, **kwargs)

        nested = SetParser()
        nested._parent = self
        nested._name = name
        #self._nested[name] = nested
        #self._sets[name] = nested

        # We also let the user create a set entry with no config. We have to
        # be careful to avoid conflicts with later added positional args, so
        # we only create this entry if the user provides help text (because why
        # else would they provide help text), allowing "add_default" to
        # override this.
        if (kwargs['add_default']
                if 'add_default' in kwargs
                else 'help' in kwargs):
            nkwargs = kwargs.copy()
            if 'add_default' in nkwargs:
                del nkwargs['add_default']
            nkwargs.setdefault('action', 'store_true')
            nested.add_argument('DELETEME', **nkwargs)

        return nested

#    def add_nestedparser_(self, name, parser):
#        """
#        Add a nested parser, this is different than a subparser in that the
#        nested parser in namespaced with long-form optional arguments instead of
#        provided a new command.
#        """
#        # I just do this a bunch
#        assert parser != self
#
#        # We only support long-form names currently
#        assert name.startswith('--')
#        self._nested__[name] = parser
#
#        # add fake arguments for help text
#        # TODO do we need get_help_args helper method?
#        for pargs, pkwargs in parser.get_help_args():
#            pargs = [re.sub('^--(.*)$', r'--%s.\1' % name[2:], arg)
#                for arg in pargs]
#            pkwargs = pkwargs.copy()
#            pkwargs.setdefault('dest', '')
#            self.add_argument(*pargs, **pkwargs)
#
#    def add_set_(self, setname, parser):
#        """
#        Extend this argument parser with a set of additional arg parsers
#        """
#        # yeah we only support long-form names currently
#        assert setname.startswith('--')
#        self._nested__[setname] = SetParser(setname, parser)
#
#        # add fake arguments for help text
#        for pargs, pkwargs in self._nested__[setname].get_help_args():
#            pkwargs = pkwargs.copy()
#            pkwargs['dest'] = ''
#            self.add_argument(*pargs, **pkwargs)
#
#    def get_help_args(self):
#        """
#        Generate fake arguments for the purpose of providing help text.
#        """
#        for pargs, pkwargs in self._optional:
#            if '--help' in pargs:
#                continue
#
#            yield pargs, pkwargs

    def parse_known_args(self, args=None, ns=None):
        if args is None:
            args = sys.argv[1:]

        # first parse out sets, this is a bit complicated
        set_prefixes = set()
        for oargs, okwargs in self._optional:
            for oarg in oargs:
                om = re.search(r'(\b[A-Z0-9]+\b)', oarg)
                if not om:
                    continue
                pattern = re.sub(r'(\b[A-Z0-9]+\b)', r'([\w-]+)', oarg)
                pattern = re.sub(r'\.', r'\.', pattern)

                # find pattern matches
                for arg in args:
                    m = re.match(pattern, arg)
                    if m:
                        set_prefixes.add((arg[:m.start(1)], m.group(1)))

                # default sets
                ns = ns or Namespace()
                ns.__dict__[oarg[2:om.start()-1]] = {}

        # create temporary parsers to extract known args
        sets = []
        for prefix, match in set_prefixes:
            tempparser = ArgumentParser(allow_abbrev=False, add_help=False)
            for oargs, okwargs in self._optional:
                if any(oarg.startswith(prefix) for oarg in oargs):
                    nargs = [re.sub(r'(\b[A-Z0-9]+\b)', match, oarg, 1)
                        for oarg in oargs]
                    nkwargs = okwargs.copy()
                    nkwargs['dest'] = re.sub(r'(\b[A-Z0-9]+\b)', match,
                        nkwargs['dest'], 1)
                    tempparser.add_argument(*nargs, **nkwargs)

            nns, args = tempparser.parse_known_args(args, Namespace())

            # turn sets into python dicts
            def dictify(ns, path):
                if not path:
                    return ns
                elif re.match(r'(\b[A-Z0-9]+\b)', path[0]):
                    return {k: dictify(v, path[1:])
                        for k, v in ns.__dict__.items()}
                else:
                    return Namespace(**{k: dictify(v, path[1:])
                        for k, v in ns.__dict__.items()})

            sets.append(dictify(nns, (prefix+'DICTME').split('.')))

        # parse!
        ns, args = super().parse_known_args(args, ns)

        # delete fake args and merge sets
        ns.__dict__ = {
            k: v for k, v in ns.__dict__.items()
            if not re.search(r'(\b[A-Z0-9]+\b)', k)}

        # create nested namespaces
        def nest(ns):
            ndict = {}
            nested = {}
            for k, v in ns.__dict__.items():
                if '.' in k:
                    scope, name = k.split('.', 1)
                    nested.setdefault(scope, {})[name] = v
                else:
                    ndict[k] = v
            for k, v in nested.items():
                ndict[k] = nest(Namespace(**v))
            return Namespace(**ndict)

        ns = nest(ns)

        for nns in sets:
            ns = merge(ns, nns)

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

#    def parse_known_args_(self, args=None, ns=None):
#        if args is None:
#            args = sys.argv[1:]
#
#        # cycle between parsers, consuming args
#        parsers = list(self._nested__.values()) + [super()]
#        parser_args = [[] for parser in parsers]
#        while args:
#            diff = []
#            for i, parser in enumerate(parsers):
#                oldargs = args
#                _, args = parser.parse_known_args(args)
#                diff = [arg for arg in oldargs if arg not in args]
#                if diff:
#                    parser_args[i].extend(diff)
#                    break
#            else:
#                break
#
#        # now apply each parser fully in turn, we do this because I don't
#        # know how to merge Namespace objects
#        parser_namespaces = {}
#        for i, (name, parser) in enumerate(self._nested__.items()):
#            parser_namespaces[name], rem = parser.parse_known_args(
#                parser_args[i])
#            assert not rem
#
#        ns, _ = super().parse_known_args(parser_args[-1], ns)
#        for name, nns in parser_namespaces.items():
#            setattr(ns, name[2:], nns)
#
#        # delete fake args
#        if '' in ns.__dict__:
#            del ns.__dict__['']
#
#        # Create nested namespaces
#        def nest(ns):
#            ndict = {}
#            nested = {}
#            for k, v in ns.__dict__.items():
#                if '.' in k:
#                    scope, name = k.split('.', 1)
#                    nested.setdefault(scope, {})[name] = v
#                else:
#                    ndict[k] = v
#            for k, v in nested.items():
#                ndict[k] = nest(Namespace(**v))
#            return Namespace(**ndict)
#
#        return nest(ns), args

    

#class SetParser:
#    """
#    This class parses a variable set where each entry satisfies
#    a provided ArgumentParser.
#    """
#    def __init__(self, name, parser):
#        # yeah we only support long-form names currently
#        assert name.startswith('--')
#        assert (hasattr(parser, '_optional') and all(arg.startswith('-')
#            for args, _ in parser._optional for arg in args))
#
#        self._name = name[2:]
#        self._parser = parser
#
#    def get_help_args(self):
#        """
#        Generate fake arguments for the purpose of providing help text.
#        """
#        for pargs, pkwargs in self._parser._optional:
#            if '--help' in pargs:
#                continue
#
#            npargs = []
#            npkwargs = pkwargs.copy()
#            for parg in pargs:
#                if parg.startswith('--'):
#                    npkwargs['metavar'] = parg[2:].split('.')[-1].upper()
#                    npargs.append('--%s.%s.%s' % (
#                        self._name, '%s' % self._name.upper(), parg[2:]))
#
#            yield npargs, npkwargs
#
#    def parse_known_args(self, args):
#        """
#        Parses out our dict args.
#
#        Returns a tuple of the Namespace and remaining args.
#        """
#        if args is None:
#            args = sys.argv[1:]
#
#        # find possible args
#        matches = set()
#        for arg in args:
#            m = re.match('--%s.([\w\.-]+)' % self._name, arg)
#            if m:
#                matches.add(m.group(1))
#
#        match_parsers = {}
#        for match in matches:
#            # create new argparser for each match
#            prefixed_parser = ArgumentParser(allow_abbrev=False, add_help=False)
#            for pargs, pkwargs in self._parser._optional:
#                if '--help' in pargs:
#                    continue
#
#                npargs = []
#                for parg in pargs:
#                    if parg.startswith('--'):
#                        npargs.append('--%s.%s.%s' % (
#                            self._name, match, parg[2:]))
#
#                prefixed_parser.add_argument(*npargs, **pkwargs)
#
#            match_parsers[match] = prefixed_parser
#
#        # cycle through matches until we consumed as many args as we can
#        match_args = {match: [] for match in matches}
#        while args:
#            for match in matches:
#                oldargs = args
#                _, args = match_parsers[match].parse_known_args(args)
#                diff = [arg for arg in oldargs if arg not in args]
#                if diff:
#                    match_args[match].extend(diff)
#                    break
#            else:
#                break
#
#        # now apply each parser fully in turn, we do this because I don't
#        # know how to merge Namespace objects
#        match_namespaces = {}
#        for match in matches:
#            nns, rem = match_parsers[match].parse_known_args(match_args[match])
#            assert not rem
#
#            prefix = '%s.%s.' % (self._name, match)
#            nns = {k[len(prefix):]: v for k, v in nns.__dict__.items()}
#            match_namespaces[match] = Namespace(**nns)
#
#        return match_namespaces, args
#
