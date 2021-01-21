#
# stdout/stderr glue, mostly a small printf
# 
# Copyright (c) 2020, Arm Limited. All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause
#

from .. import glue

C_MINIMAL_PRINTF = """
ssize_t __box_cbprintf(
        ssize_t (*write)(void *ctx, const void *buf, size_t size), void *ctx,
        const char *format, va_list args) {
    const char *p = format;
    ssize_t res = 0;
    while (true) {
        // first consume everything until a '%%'
        size_t skip = strcspn(p, "%%");
        if (skip > 0) {
            ssize_t nres = write(ctx, p, skip);
            if (nres < 0) {
                return nres;
            }
            res += nres;
        }

        p += skip;

        // hit end of string?
        if (!*p) {
            return res;
        }

        // format parser
        bool zero_justify = false;
        bool left_justify = false;
        bool precision_mode = false;
        size_t width = 0;
        size_t precision = 0;

        char mode = 'c';
        uint32_t value = 0;
        size_t size = 0;

        for (;; p++) {
            if (p[1] >= '0' && p[1] <= '9') {
                // precision/width
                if (precision_mode) {
                    precision = precision*10 + (p[1]-'0');
                } else if (p[1] > '0' || width > 0) {
                    width = width*10 + (p[1]-'0');
                } else {
                    zero_justify = true;
                }

            } else if (p[1] == '*') {
                // dynamic precision/width
                if (precision_mode) {
                    precision = va_arg(args, size_t);
                } else {
                    width = va_arg(args, size_t);
                }

            } else if (p[1] == '.') {
                // switch mode
                precision_mode = true;

            } else if (p[1] == '-') {
                // left-justify
                left_justify = true;

            } else if (p[1] == '%%') {
                // single '%%'
                mode = 'c';
                value = '%%';
                size = 1;
                break;

            } else if (p[1] == 'c') {
                // char
                mode = 'c';
                value = va_arg(args, int);
                size = 1;
                break;

            } else if (p[1] == 's') {
                // string
                mode = 's';
                const char *s = va_arg(args, const char *);
                value = (uint32_t)s;
                // find size, don't allow overruns
                size = 0;
                while (s[size] && (precision == 0 || size < precision)) {
                    size += 1;
                }
                break;

            } else if (p[1] == 'd' || p[1] == 'i') {
                // signed decimal number
                mode = 'd';
                int32_t d = va_arg(args, int32_t);
                value = (uint32_t)d;
                size = 0;
                if (d < 0) {
                    size += 1;
                    d = -d;
                }
                for (uint32_t t = d; t > 0; t /= 10) {
                    size += 1;
                }
                if (size == 0) {
                    size += 1;
                }
                break;

            } else if (p[1] == 'u') {
                // unsigned decimal number
                mode = 'u';
                value = va_arg(args, uint32_t);
                size = 0;
                for (uint32_t t = value; t > 0; t /= 10) {
                    size += 1;
                }
                if (size == 0) {
                    size += 1;
                }
                break;

            } else if (p[1] >= ' ' && p[1] <= '?') {
                // unknown modifier? skip

            } else {
                // hex or unknown character, terminate

                // make it prettier for pointers
                if (!(p[1] == 'x' || p[1] == 'X')) {
                    zero_justify = true;
                    width = 2*sizeof(void*);
                }

                // hexadecimal number
                mode = 'x';
                value = va_arg(args, uint32_t);
                size = 0;
                for (uint32_t t = value; t > 0; t /= 16) {
                    size += 1;
                }
                if (size == 0) {
                    size += 1;
                }
                break;
            }
        }

        // consume the format
        p += 2;

        // format printing
        if (!left_justify) {
            for (ssize_t i = 0; i < (ssize_t)width-(ssize_t)size; i++) {
                char c = (zero_justify) ? '0' : ' ';
                ssize_t nres = write(ctx, &c, 1);
                if (nres < 0) {
                    return nres;
                }
                res += nres;
            }
        }

        if (mode == 'c') {
            ssize_t nres = write(ctx, &value, 1);
            if (nres < 0) {
                return nres;
            }
            res += nres;
        } else if (mode == 's') {
            ssize_t nres = write(ctx, (const char*)(uintptr_t)value, size);
            if (nres < 0) {
                return nres;
            }
            res += nres;
        } else if (mode == 'x') {
            for (ssize_t i = size-1; i >= 0; i--) {
                uint32_t digit = (value >> (4*i)) & 0xf;

                char c = ((digit >= 10) ? ('a'-10) : '0') + digit;
                ssize_t nres = write(ctx, &c, 1);
                if (nres < 0) {
                    return nres;
                }
                res += nres;
            }
        } else if (mode == 'd' || mode == 'u') {
            ssize_t i = size-1;

            if (mode == 'd' && (int32_t)value < 0) {
                ssize_t nres = write(ctx, "-", 1);
                if (nres < 0) {
                    return nres;
                }
                res += nres;

                value = -value;
                i -= 1;
            }

            for (; i >= 0; i--) {
                uint32_t temp = value;
                for (int j = 0; j < i; j++) {
                    temp /= 10;
                }
                uint32_t digit = temp %% 10;

                char c = '0' + digit;
                ssize_t nres = write(ctx, &c, 1);
                if (nres < 0) {
                    return nres;
                }
                res += nres;
            }
        }

        if (left_justify) {
            for (ssize_t i = 0; i < (ssize_t)width-(ssize_t)size; i++) {
                char c = ' ';
                ssize_t nres = write(ctx, &c, 1);
                if (nres < 0) {
                    return nres;
                }
                res += nres;
            }
        }
    }
}

static ssize_t __box_vprintf_write(void *ctx, const void *buf, size_t size) {
    return __box_write((int32_t)ctx, buf, size);
}

%(visibility)s
ssize_t __wrap_vprintf(const char *format, va_list args) {
    return __box_cbprintf(__box_vprintf_write, (void*)1, format, args);
}

%(visibility)s
ssize_t __wrap_printf(const char *format, ...) {
    va_list args;
    va_start(args, format);
    ssize_t res = __wrap_vprintf(format, args);
    va_end(args);
    return res;
}

%(visibility)s
ssize_t __wrap_vfprintf(FILE *f, const char *format, va_list args) {
    int32_t fd = (f == stdout) ? 1 : 2;
    return __box_cbprintf(__box_vprintf_write, (void*)fd, format, args);
}

%(visibility)s
ssize_t __wrap_fprintf(FILE *f, const char *format, ...) {
    va_list args;
    va_start(args, format);
    ssize_t res = __wrap_vfprintf(f, format, args);
    va_end(args);
    return res;
}
"""

C_HOOKS = """
%(visibility)s
int __wrap_fflush(FILE *f) {
    int32_t fd = (f == stdout) ? 1 : 2;
    return __box_flush(fd);
}
"""

GCC_HOOKS = """
#if defined(__GNUC__)
int _write(int handle, const char *buffer, int size) {
    return __box_write(handle, (const uint8_t*)buffer, size);
}
#endif
"""

WASM_HOOKS = """
ssize_t __wrap_writev(int fd, const struct iovec *iov, int count) {
    size_t sum = 0;
    for (int i = 0; i < count; i++) {
        ssize_t res = __box_write(fd, iov[i].iov_base, iov[i].iov_len);
        if (res < 0) {
            return res;
        }

        sum += res;
    }

    return sum;
}

int __isatty(int fd) {
    return true;
}

off_t __stdio_seek(FILE *f, off_t off, int whence) {
    return -ESPIPE;
}

int __stdio_close(FILE *f) {
    return 0;
}
"""

RUST_HOOKS = '''
pub fn write(fd: i32, buffer: &[u8]) -> Result<usize> {
    extern "C" {
        fn __box_write(fd: i32, buffer: *const u8, size: usize) -> isize;
    }

    let res = unsafe { __box_write(fd, buffer.as_ptr(), buffer.len()) };
    if res < 0 {
        Err(Error::new(-res as u32).unwrap())?;
    }

    Ok(res as usize)
}

pub fn flush(fd: i32) -> Result<()> {
    extern "C" {
        fn __box_flush(fd: i32) -> i32;
    }

    let res = unsafe { __box_flush(fd) };
    if res < 0 {
        Err(Error::new(-res as u32).unwrap())?;
    }

    Ok(())
}
'''

RUST_STDOUT = '''
/// %(name)s implementation
pub struct %(Name)s;

pub fn %(name)s() -> %(Name)s {
    %(Name)s
}

impl %(Name)s {
    pub fn write(&mut self, buf: &[u8]) -> Result<usize> {
        write(%(fd)d, buf)
    }

    pub fn flush(&mut self) -> Result<()> {
        flush(%(fd)d)
    }
}

impl fmt::Write for %(Name)s {
    fn write_str(&mut self, s: &str) -> fmt::Result {
        match self.write(s.as_bytes()) {
            Ok(_) => Ok(()),
            Err(_) => Err(fmt::Error),
        }
    }
}

#[macro_export]
macro_rules! %(print)s {
    ($($arg:tt)*) => ({
        use ::core::fmt::Write;
        ::core::write!(%(Name)s, $($arg)*).unwrap();
    });
}

#[macro_export]
macro_rules! %(print)sln {
    () => ({
        $crate::%(print)s!("\\n");
    });
    ($($arg:tt)*) => ({
        $crate::%(print)s!($($arg)*);
        $crate::%(print)s!("\\n");
    });
}
'''

class WriteGlue(glue.Glue):
    """
    Helper layer for handling __box_write and friends.
    """
    __name = 'write_glue'
    def box(self, box):
        super().box(box)
        self.__write_hook = box.addimport(
            '__box_write',
            'fn(i32 fd, const u8 buffer[size], usize size) -> errsize',
            scope=box.name, source=self.__name, weak=True,
            doc="Provides a minimal implementation of stdout to the box. "
                "The exact behavior depends on the superbox's implementation "
                "of __box_write. If none is provided, __box_write links but "
                "does nothing.")
        self.__flush_hook = box.addimport(
            '__box_flush', 'fn(i32 fd) -> err',
            scope=box.name, source=self.__name, weak=True,
            doc="Provides a minimal implementation of stdout to the box. "
                "The exact behavior depends on the superbox's implementation "
                "of __box_flush. If none is provided, __box_flush links but "
                "does nothing.")

    def __build_common_prologue(self, output, box):
        output.decls.append('%(fn)s;',
            fn=output.repr_fn(self.__write_hook),
            doc=self.__write_hook.doc)
        output.decls.append('%(fn)s;',
            fn=output.repr_fn(self.__flush_hook),
            doc=self.__flush_hook.doc)

    def build_h_prologue(self, output, box):
        super().build_h_prologue(output, box)
        self.__build_common_prologue(output, box)

    def build_c_prologue(self, output, box):
        super().build_c_prologue(output, box)
        self.__build_common_prologue(output, box)

    def build_wasm_h_prologue(self, output, box):
        super().build_wasm_h_prologue(output, box)
        self.__build_common_prologue(output, box)

    def build_wasm_c_prologue(self, output, box):
        super().build_wasm_c_prologue(output, box)
        self.__build_common_prologue(output, box)

    def __build_common_c(self, output, box):
        output.decls.append('//// __box_write glue ////')
        if not self.__write_hook.link:
            # defaults to noop
            out = output.decls.append()
            out.printf('ssize_t __box_write(int32_t fd, '
                'const void *buffer, size_t size) {')
            with out.indent():
                out.printf('return size;')
            out.printf('}')
        elif self.__write_hook.link.export.alias != '__box_write':
            # jump to correct implementation
            out = output.decls.append()
            out.printf('ssize_t __box_write(int32_t fd, '
                'const void *buffer, size_t size) {')
            with out.indent():
                out.printf('return %(alias)s(fd, buffer, size);',
                    alias=self.__write_hook.link.export.alias)
            out.printf('}')

        if not self.__flush_hook.link:
            # defaults to noop
            out = output.decls.append()
            out.printf('int __box_flush(int32_t fd) {')
            with out.indent():
                out.printf('return 0;')
            out.printf('}')
        elif self.__flush_hook.link.export.alias != '__box_flush':
            # jump to correct implementation
            out = output.decls.append()
            out.printf('int __box_flush(int32_t fd) {')
            with out.indent():
                out.printf('return %(alias)s(fd);',
                    alias=self.__flush_hook.link.export.alias)
            out.printf('}')

        if output.printf_impl == 'minimal':
            output.includes.append('<stdarg.h>')
            output.includes.append('<string.h>')
            out = output.decls.append()
            out.printf(C_MINIMAL_PRINTF)

        if not output.no_stdlib_hooks:
            output.decls.append(C_HOOKS)

    def build_c(self, output, box):
        super().build_c(output, box)

        with output.pushattrs(
                visibility='__attribute__((used))'):
            self.__build_common_c(output, box)

            if not output.no_stdlib_hooks:
                output.decls.append(GCC_HOOKS)

    def build_wasm_c(self, output, box):
        super().build_wasm_c(output, box)

        with output.pushattrs(
                visibility='__attribute__((visibility("hidden")))'):
            self.__build_common_c(output, box)

            if not output.no_stdlib_hooks:
                output.decls.append(WASM_HOOKS)

    def build_mk(self, output, box):
        super().build_mk(output, box)

        out = output.decls.append()
        out.printf('### __box_write glue ###')
        if ('c' in box.outputs and
                not box.outputs[box.outputs.index('c')].no_stdlib_hooks):
            if (box.outputs[box.outputs.index('c')]
                    .printf_impl == 'minimal'):
                out.printf('override LDFLAGS += -Wl,--wrap,printf')
                out.printf('override LDFLAGS += -Wl,--wrap,vprintf')
                out.printf('override LDFLAGS += -Wl,--wrap,fprintf')
                out.printf('override LDFLAGS += -Wl,--wrap,vfprintf')
            out.printf('override LDFLAGS += -Wl,--wrap,fflush')
        if ('wasm_c' in box.outputs and
                not box.outputs[box.outputs.index('wasm_c')].no_stdlib_hooks):
            if (box.outputs[box.outputs.index('wasm_c')]
                    .printf_impl == 'minimal'):
                out.printf('override WASMLDFLAGS += -Wl,--wrap,printf')
                out.printf('override WASMLDFLAGS += -Wl,--wrap,vprintf')
                out.printf('override WASMLDFLAGS += -Wl,--wrap,fprintf')
                out.printf('override WASMLDFLAGS += -Wl,--wrap,vfprintf')
            out.printf('override WASMLDFLAGS += -Wl,--wrap,writev')
            out.printf('override WASMLDFLAGS += -Wl,--wrap,fflush')

    def __build_rust_lib_common(self, output, box):
        output.uses.append('core::fmt')
        output.decls.append(RUST_HOOKS)
        output.decls.append(RUST_STDOUT,
            name='stdout', Name='Stdout',
            fd=1, print='print')
        output.decls.append(RUST_STDOUT,
            name='stderr', Name='Stderr',
            fd=2, print='eprint')

    def build_rust_lib(self, output, box):
        super().build_rust_lib(output, box)
        self.__build_rust_lib_common(output, box)

    def build_wasm_rust_lib(self, output, box):
        super().build_wasm_rust_lib(output, box)
        self.__build_rust_lib_common(output, box)
        

