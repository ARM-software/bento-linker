#
# Rust outputer
# 
# Copyright (c) 2020, Arm Limited. All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause
#
from .. import outputs
from ..box import Fn
import io
import textwrap
import itertools as it


@outputs.output
class RustLibOutput(outputs.Output):
    """
    Path of Rust file to place the generated bento-box library.
    """
    __argname__ = "rust_lib"
    __arghelp__ = __doc__

    def __init__(self, path=None):
        super().__init__(path)

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
    def repr_arg(arg, name=None, ns=False, ret=False):
        name = name if name is not None else arg.name
        arg = ''.join([
            (name if name else '_') + ': ' if name != '' else '',
            'Option<' if arg.isnullable() else '',
            ('&\'static mut ' if arg.ismut() else '&\'static ')
            if arg.isptr() and ret else
            ('&mut ' if arg.ismut() else '&')
            if arg.isptr() else
            '',
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
        if ns:
            arg = arg.replace('Result', '%s::Result' % ns)
        return arg

    @staticmethod
    def repr_fn(fn, name=None, attrs=[], ns=False):
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
            ', '.join(RustLibOutput.repr_arg(arg, name, ns)
                for arg, name in zip(fn.args, fn.argnames())
                if name not in asizes),
            ')',
            ' -> !' if fn.isnoreturn() else
            ' -> %s' % RustLibOutput.repr_arg(fn.rets[0], '', ns, True)
            if fn.rets else
            '']))

    @staticmethod
    def repr_rawarg(arg, name=None):
        name = name if name is not None else arg.name
        return ''.join([
            (name if name else '_') + ': ' if name != '' else '',
            ('*mut ' if arg.ismut() else '*const ') if arg.isptr() else '',
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
            ', '.join(RustLibOutput.repr_rawarg(arg, name)
                for arg, name in zip(fn.args, fn.argnames())),
            ')',
            ' -> !' if fn.isnoreturn() else
            ' -> %s' % RustLibOutput.repr_rawarg(fn.rets[0], '') if fn.rets else
            '']))

    @staticmethod
    def build_c2rust(out, arg, name=None, adeps={}):
        name = name if name is not None else arg.name
        with out.pushattrs(name=name, asize=arg.asize()):
            # type conversions
            if arg.iserr():
                out.printf('let %(name)s = match %(name)s >= 0 {')
                with out.indent():
                    if arg.prim() == 'err':
                        out.printf('true => Ok(()),')
                    else:
                        out.printf('true => Ok('
                            'u%(width)s::try_from(%(name)s).unwrap()),',
                            width=arg.prim()[3:])
                    out.printf('false => Err(Error::new('
                        'u32::try_from(%(name)s).unwrap()).unwrap()),')
                out.printf('};')
            if arg.isptr() and not isinstance(arg.asize(), str):
                if arg.isarray():
                    out.printf('let %(name)s = %(name)s '
                        'as *%(const)s [%(prim)s; %(asize)s];',
                        const='const' if arg.isconst() else 'mut',
                        prim=arg.prim())
                if arg.isnullable():
                    out.printf('let %(name)s = unsafe { '
                        '%(name)s.%(as_ref)s() };',
                        as_ref='as_mut' if arg.ismut() else 'as_ref')
                else:
                    out.printf('let %(name)s = unsafe { &%(mut)s*%(name)s };',
                        mut='mut ' if arg.ismut() else '')
            if isinstance(arg.asize(), str):
                if arg.isnullable():
                    out.printf('let %(name)s = match !%(name)s.is_null() {')
                    out.pushindent()
                    out.printf('true => {')
                    out.pushindent()
                out.printf('let %(name)s = unsafe { '
                    'slice::%(from_raw_parts)s(%(name)s, %(asize)s) };',
                    from_raw_parts='from_raw_parts_mut'
                        if arg.ismut() else
                        'from_raw_parts')
                if arg.isnullable():
                    out.printf('Some(%(name)s)')
                    out.popindent()
                    out.printf('},')
                    out.printf('false => None,')
                    out.popindent()
                    out.printf('};')

    @staticmethod
    def build_rust2c(out, arg, name=None, adeps={}):
        name = name if name is not None else arg.name
        with out.pushattrs(name=name, asize=arg.asize()):
            # type conversions
            if arg.iserr():
                out.printf('let %(name)s = match %(name)s {')
                with out.indent():
                    if arg.prim() == 'err':
                        out.printf('Ok(()) => 0,')
                    elif arg.prim() == 'errsize':
                        out.printf('Ok(x) => isize::try_from(x).unwrap(),')
                    elif arg.prim() == 'err64':
                        out.printf('Ok(x) => i64::try_from(x).unwrap(),')
                    else:
                        out.printf('Ok(x) => i32::try_from(x).unwrap(),')

                    if arg.prim() == 'errsize':
                        out.printf('Err(err) => isize::try_from('
                            '-err.get_i32()).unwrap(),')
                    elif arg.prim() == 'err64':
                        out.printf('Err(err) => i64::from(-err.get_i32()),')
                    else:
                        out.printf('Err(err) => -err.get_i32(),')
                out.printf('};')
            if arg.isptr():
                if arg.isnullable():
                    if not isinstance(arg.asize(), str):
                        out.printf('let %(name)s '
                            '= match %(name)s {')
                    else:
                        out.printf('let (%(name)s, %(asize)s) '
                            '= match %(name)s {')
                    out.pushindent()
                    out.printf('Some(%(name)s) => {')
                    out.pushindent()
                if not isinstance(arg.asize(), str):
                    out.printf('let %(name)s = %(name)s '
                        'as *%(mut)s %(prim)s;',
                        mut='mut' if arg.ismut() else 'const',
                        prim=arg.prim())
                else:
                    out.printf('let (%(name)s, %(asize)s) '
                        '= (%(name)s.%(as_ptr)s(), %(name)s.len()); ',
                        as_ptr='as_mut_ptr' if arg.ismut() else 'as_ptr')
                if arg.isnullable():
                    if not isinstance(arg.asize(), str):
                        out.printf('%(name)s')
                    else:
                        out.printf('(%(name)s, %(asize)s)')
                    out.popindent()
                    out.printf('},')
                    if not isinstance(arg.asize(), str):
                        out.printf('None => ptr::%(null)s(),',
                            null='null_mut' if arg.ismut() else 'null')
                    else:
                        out.printf('None => (ptr::%(null)s(), 0),',
                            null='null_mut' if arg.ismut() else 'null')
                    out.popindent()
                    out.printf('};')
                
    def build_prologue(self, box):
        # misc
        self.inner_attrs.append('no_std')

        out = self.decls.append()
        out.printf('extern crate bento_macros;')
        out.printf('pub use bento_macros::export;')

        # we use this in conversions
        out = self.decls.append()
        out.printf('pub mod import {')
        with out.indent():
            out.printf('#[allow(unused_imports)]')
            out.printf('use core::{convert::TryFrom, ptr, slice};')
            out.printf('#[allow(unused_imports)]')
            out.printf('use crate::{Result, Error};')
            for j, import_ in enumerate(
                    import_ for import_ in box.imports
                    if import_.source == box):
                # find array dependencies to convert correctly
                adeps = {}
                for arg, name in it.chain(
                        zip(import_.args, import_.argnames()),
                        zip(import_.rets, import_.retnames())):
                    if isinstance(arg.asize(), str):
                        adeps[arg.asize()] = (arg, name)

                with out.pushattrs(
                        doc=import_.doc,
                        alias=import_.alias,
                        fn=self.repr_fn(import_),
                        rawfn=self.repr_rawfn(import_),
                        retname=import_.retname()):
                    out.printf()
                    out.printf('pub %(fn)s {')
                    with out.indent():
                        # first the extern decl
                        out.printf('extern "C" {')
                        with out.indent():
                            out.printf('pub %(rawfn)s;')
                        out.printf('}')
                        for arg, name in sorted(
                                zip(import_.args, import_.argnames()),
                                # half-ass topo-sort for dependencies
                                key=lambda p: (
                                    not isinstance(p[0].asize(), str))):
                            self.build_rust2c(out, arg, name, adeps=adeps)
                        out.writef('let %(retname)s = unsafe { %(alias)s(')
                        for i, (arg, name) in enumerate(
                                zip(import_.args, import_.argnames())):
                            out.writef(name)
                            if i != len(import_.args)-1:
                                out.writef(', ')
                        out.printf(') };')
                        if import_.rets:
                            self.build_c2rust(out,
                                import_.rets[0], import_.retname(), adeps=adeps)
                        out.printf('%(retname)s')
                    out.printf('}')
        out.printf('}')

        # exports
        out = self.decls.append()
        out.printf('pub mod export {')
        with out.indent():
            out.printf('#[allow(unused_imports)]')
            out.printf('use bento_macros::export_export;')
            for j, export in enumerate(
                    export for export in box.exports
                    if export.source == box):
                # find array dependencies to convert correctly
                adeps = {}
                for arg, name in it.chain(
                        zip(export.args, export.argnames()),
                        zip(export.rets, export.retnames())):
                    if isinstance(arg.asize(), str):
                        adeps[arg.asize()] = (arg, name)

                with out.pushattrs(
                        alias=export.alias,
                        fnnoname=self.repr_fn(export, name='',
                            ns='__box_exports'),
                        rawfn=self.repr_rawfn(export),
                        retname=export.retname()):
                    out.printf()
                    out.printf('#[export_export(type=%(fnnoname)s)]')
                    out.printf('pub %(rawfn)s {')
                    with out.indent():
                        # we use this in conversions
                        out.printf('#[allow(unused_imports)]')
                        out.printf('use core::{convert::TryFrom, ptr, slice};')
                        out.printf('#[allow(unused_imports)]')
                        out.printf('use __box_exports::{Result, Error};')
                        for arg, name in sorted(
                                zip(export.args, export.argnames()),
                                # half-ass topo-sort for dependencies
                                key=lambda p: isinstance(p[0].asize(), str)):
                            self.build_c2rust(out, arg, name, adeps=adeps)
                        out.writef('let %(retname)s = __box_export_%(alias)s(')
                        # remove dependecies as they should be consumed
                        # in conversion
                        export_nargs = [(arg, name) for arg, name in
                            zip(export.args, export.argnames())
                            if not name in adeps]
                        for i, (arg, name) in enumerate(export_nargs):
                            out.writef(name)
                            if i != len(export_nargs)-1:
                                out.writef(', ')
                        out.printf(');')
                        if export.rets:
                            self.build_rust2c(out,
                                export.rets[0], export.retname(), adeps=adeps)
                        out.printf('%(retname)s')
                    out.printf('}')
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

        for decl in self.decls:
            if 'doc' in decl:
                for line in textwrap.wrap(decl['doc'], width=78-4):
                    self.print('/// %s' % line)
            self.print(str(decl).strip())
            self.print()

        return super().getvalue()
