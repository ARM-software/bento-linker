from .. import outputs
from ..box import Fn
import io
import textwrap
import itertools as it

@outputs.output
class RustOutput(outputs.Output):
    """
    Name of rust file to place the generated bento-box crate.
    """
    __argname__ = "rs"
    __arghelp__ = __doc__
    @classmethod
    def __argparse__(cls, parser, **kwargs):
        super().__argparse__(parser, **kwargs)

        parser.add_argument('--no_runtime_logic', type=bool,
            help='Don\'t emit the box runtime logic, requires runtime '
                'logic to be output in another source file. Currently required '
                'as pure Rust runtime logic is not currently supported but may '
                'be added in the future.')

    def __init__(self, path=None, no_runtime_logic=None):
        super().__init__(path)

        self.no_runtime_logic = no_runtime_logic or False
        assert self.no_runtime_logic, ("Runtime logic in Rust output currently "
            "unsupported. Requires the no_runtime_logic flag.")

        self.inner_attrs = outputs.OutputField(self)
        self.uses = outputs.OutputField(self)
        self.import_uses = outputs.OutputField(self)
        self.imports = outputs.OutputField(self, indent=4)
        self.export_uses = outputs.OutputField(self)
        self.exports = outputs.OutputField(self, indent=4)
        self.linkage_uses = outputs.OutputField(self)
        self.linkages = outputs.OutputField(self, indent=4)
        self.decls = outputs.OutputField(self)

    @staticmethod
    def repr_arg(arg, name=None):
        name = name if name is not None else arg.name
        return ''.join([
            (name if name else '_') + ': ' if name != '' else '',
            'Option<' if arg.isnullable() else '',
            ('&mut ' if arg.ismut() else '&') if arg.isptr() else '',
            '[' if arg.asize() is not None else '',
            'bool'     if arg.prim() == 'bool' else
            'Result<()>' if arg.prim() == 'err' else
            'Result<u%s>' % arg.prim()[3:]
                if arg.prim().startswith('err') else
            arg.prim() if arg.prim().startswith('i') else
            arg.prim() if arg.prim().startswith('u') else
            arg.prim() if arg.prim().startswith('f') else
            '???',
            '; %d]' % arg.asize() if isinstance(arg.asize(), int) else
            ']' if arg.asize() is not None else
            '',
            '>' if arg.isnullable() else ''])

    @staticmethod
    def repr_fn(fn, name=None, attrs=[]):
        name = name if name is not None else fn.alias
        asizes = set()
        for arg in fn.args:
            if isinstance(arg.asize(), str):
                asizes.add(arg.asize())
        return ''.join(it.chain(
            (attr + ('\n' if attr.startswith('#') else ' ')
                for attr in attrs), [
            'fn',
            ' %s' % name if name else '',
            '(',
            ', '.join(RustOutput.repr_arg(arg, name)
                for arg, name in zip(fn.args, fn.argnames())
                if name not in asizes),
            ')',
            ' -> !' if fn.isnoreturn() else
            ' -> %s' % RustOutput.repr_arg(fn.rets[0], '') if fn.rets else
            '']))

    @staticmethod
    def repr_rawarg(arg, name=None):
        name = name if name is not None else arg.name
        return ''.join([
            (name if name else '_') + ': ' if name != '' else '',
            ('*mut ' if arg.ismut() else '*') if arg.isptr() else '',
            'bool'     if arg.prim() == 'bool' else
            'isize'    if arg.prim() == 'errsize' else
            'i64'      if arg.prim() == 'err64' else
            'i32'      if arg.prim().startswith('err') else
            arg.prim() if arg.prim().startswith('i') else
            arg.prim() if arg.prim().startswith('u') else
            arg.prim() if arg.prim().startswith('f') else
            '???'])

    @staticmethod
    def repr_rawfn(fn, name=None, attrs=[]):
        name = name if name is not None else fn.alias
        return ''.join(it.chain(
            (attr + ('\n' if attr.startswith('#') else ' ')
                for attr in attrs), [
            'fn',
            ' %s' % name if name else '',
            '(',
            ', '.join(RustOutput.repr_rawarg(arg, name)
                for arg, name in zip(fn.args, fn.argnames())),
            ')',
            ' -> !' if fn.isnoreturn() else
            ' -> %s' % RustOutput.repr_rawarg(fn.rets[0], '') if fn.rets else
            '']))

    @staticmethod
    def build_convertfrom(out, arg, name=None):
        name = name if name is not None else arg.name
        with out.pushattrs(name=name):
            if arg.iserr():
                out.printf('let %(name)s = if %(name)s >= 0 {')
                with out.indent():
                    if arg.prim() == 'err':
                        out.printf('Ok(())')
                    else:
                        out.printf('Ok('
                            'u%(width)s::try_from(%(name)s).unwrap())',
                            width=arg.prim()[3:])
                out.printf('} else {')
                with out.indent():
                    out.printf('Err(Error::new('
                        'u32::try_from(%(name)s).unwrap()))')
                out.printf('};')
            if arg.isptr():
                if arg.isarray():
                    out.printf('let %(name)s = %(name)s '
                        'as *%(const)s [%(prim)s; %(size)d];',
                        const='const' if arg.isconst() else 'mut',
                        prim=arg.prim(),
                        size=arg.asize())
                out.printf('let %(name)s = unsafe {')
                with out.indent():
                    if arg.ismut():
                        out.printf('%(name)s.as_mut()')
                    else:
                        out.printf('%(name)s.as_ref()')
                out.printf('};')
                if arg.isnullable():
                    out.printf('let %(name)s = '
                        'if let Some(%(name)s) = %(name)s {')
                    with out.indent():
                        out.printf('Some(%(name)s)')
                    out.printf('} else {')
                    with out.indent():
                        out.printf('None')
                    out.printf('};')
                else:
                    out.printf('let %(name)s = %(name)s.unwrap();')

    @staticmethod
    def build_convertto(out, arg, name=None):
        name = name if name is not None else arg.name
        with out.pushattrs(name=name):
            if arg.iserr():
                out.printf('let %(name)s = match %(name)s {')
                with out.indent():
                    if arg.prim() == 'err':
                        out.printf('Ok(()) => 0,')
                    elif arg.width() <= 32:
                        out.printf('Ok(x) => i32::try_from(x).unwrap(),')
                    else:
                        out.printf('Ok(x) => i64::try_from(x).unwrap(),')

                    if arg.width() <= 32:
                        out.printf('Err(err) => -err.get_i32(),')
                    else:
                        out.printf('Err(err) => i64::from(-err.get_i32()),')
                out.printf('};')
            # TODO arrays w/wo sizes
            if arg.isptr():
                if arg.isnullable():
                    out.printf('let %(name)s = '
                        'if let Some(%(name)s) = %(name)s {')
                    with out.indent():
                        out.printf('%(name)s')
                    out.printf('} else {')
                    with out.indent():
                        if arg.ismut():
                            out.printf('ptr::null_mut()')
                        else:
                            out.printf('ptr::null()')
                    out.printf('};')
                out.printf('let %(name)s = %(name)s '
                    'as *%(const)s %(prim)s;',
                    const='mut' if arg.ismut() else 'const',
                    prim=arg.prim())
                
    def build_prologue(self, box):
        # imports
        self.import_uses.append('super::linkage')
        self.import_uses.append('super::Error')
        self.import_uses.append('super::Result')
        self.import_uses.append('core::convert::TryFrom')
        self.import_uses.append('core::ptr')
        for i, import_ in enumerate(
                import_ for import_ in box.imports
                if import_.source == box):
            out = self.imports.append(
                doc=import_.doc,
                alias=import_.alias,
                fn=self.repr_fn(import_),
                rawfn=self.repr_rawfn(import_),
                retname=import_.retname())
            out.printf('#[allow(dead_code)]')
            out.printf('pub %(fn)s {')
            with out.indent():
                # first the extern decl
                out.printf('extern "C" {')
                with out.indent():
                    out.printf('pub %(rawfn)s;')
                out.printf('}')
                out.printf()

                for arg, name in zip(import_.args, import_.argnames()):
                    self.build_convertto(out, arg, name)
                out.printf('let %(retname)s = unsafe {')
                with out.indent():
                    out.writef('%(alias)s(')
                    for i, (arg, name) in enumerate(
                            zip(import_.args, import_.argnames())):
                        out.writef(name)
                        if i != len(import_.args)-1:
                            out.writef(', ')
                    out.printf(')')
                out.printf('};')
                if import_.rets:
                    self.build_convertfrom(out,
                        import_.rets[0], import_.retname())
                out.printf('%(retname)s')
            out.printf('}')

        # exports
        self.export_uses.append('super::Error')
        self.export_uses.append('super::Result')
        out = self.exports.append()
        out.printf('// type check')
        for i, export in enumerate(
                export for export in box.exports
                if export.source == box):
            out.printf('const _: %(fn)s = crate::%(alias)s;',
                alias=export.alias,
                fn=self.repr_fn(export, ''))

        out = self.exports.append()
        out.printf('// redeclaration')
        for i, export in enumerate(
                export for export in box.exports
                if export.source == box):
            out.printf('pub use crate::%(name)s;',
                name=export.alias)

        # linkages
        self.linkage_uses.append('core::convert::TryFrom')
        self.linkage_uses.append('core::ptr')
        if any(export for export in box.exports
                if export.source == box):
            self.linkage_uses.append('super::export')
        for i, export in enumerate(
                export for export in box.exports
                if export.source == box):
            out = self.linkages.append(
                alias=export.alias,
                rawfn=self.repr_rawfn(export),
                retname=export.retname())
            if i == 0:
                out.printf('// export linkage')
            out.printf('#[export_name="%(alias)s"]')
            out.printf('extern "C" %(rawfn)s {')
            with out.indent():
                for arg, name in zip(export.args, export.argnames()):
                    self.build_convertfrom(out, arg, name)
                out.writef('let %(retname)s = export::%(alias)s(')
                for i, (arg, name) in enumerate(
                        zip(export.args, export.argnames())):
                    out.writef(name)
                    if i != len(export.args)-1:
                        out.writef(', ')
                out.printf(');')
                if export.rets:
                    self.build_convertto(out,
                        export.rets[0], export.retname())
                out.printf('%(retname)s')
            out.printf('}')

    def getvalue(self):
        self.seek(0)
        self.printf('////// AUTOGENERATED //////')

        inner_attrs = set()
        for attr in self.inner_attrs:
            inner_attrs.add(str(attr))
        for attr in sorted(inner_attrs):
            self.printf('#![%(attr)s]', attr=str(attr))

        uses = set()
        for use in self.uses:
            uses.add(str(use))
        for use in sorted(uses):
            self.printf('use %(use)s;', use=use)

        self.print()

        if self.imports:
            self.print('/// box imports')
            self.print('pub mod import {')
            uses = set()
            for use in self.import_uses:
                uses.add(str(use))
            for use in sorted(uses):
                self.printf(4*' '+'#[allow(unused_imports)]')
                self.printf(4*' '+'use %(use)s;', use=use)
            if uses:
                self.print()
            for i, import_ in enumerate(self.imports):
                if 'doc' in import_:
                    for line in textwrap.wrap(import_['doc'], width=78-4-4):
                        self.print('/// %s' % line)
                self.print(4*' '+str(import_).strip())
                if i != len(self.imports)-1:
                    self.print()
            self.print('}')
            self.print()

        if self.exports:
            self.print('/// box exports')
            self.print('pub mod export {')
            uses = set()
            for use in self.export_uses:
                uses.add(str(use))
            for use in sorted(uses):
                self.printf(4*' '+'#[allow(unused_imports)]')
                self.printf(4*' '+'use %(use)s;', use=use)
            if uses:
                self.print()
            for i, export in enumerate(self.exports):
                if 'doc' in export:
                    for line in textwrap.wrap(export['doc'], width=78-4-4):
                        self.print(4*' '+'/// %s' % line)
                self.print(4*' '+str(export).strip())
                if i != len(self.exports)-1:
                    self.print()
            self.print('}')
            self.print()

        if self.linkages:
            self.print('/// internal linkage')
            self.print('mod linkage {')
            uses = set()
            for use in self.linkage_uses:
                uses.add(str(use))
            for use in sorted(uses):
                self.printf(4*' '+'#[allow(unused_imports)]')
                self.printf(4*' '+'use %(use)s;', use=use)
            if uses:
                self.print()
            for i, linkage in enumerate(self.linkages):
                if 'doc' in linkage:
                    for line in textwrap.wrap(linkage['doc'], width=78-4-4):
                        self.print(4*' '+'/// %s' % line)
                self.print(4*' '+str(linkage).strip())
                if i != len(self.linkages)-1:
                    self.print()
            self.print('}')
            self.print()

        for decl in self.decls:
            if 'doc' in decl:
                for line in textwrap.wrap(decl['doc'], width=78-4):
                    self.print('/// %s' % line)
            self.print(str(decl).strip())
            self.print()

        return super().getvalue()
