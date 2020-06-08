from .. import runtimes

BOX_MINIMAL_PRINTF = """
ssize_t __box_cbprintf(
        ssize_t (*write)(void *ctx, const void *buf, size_t size), void *ctx,
        const char *format, va_list args) {
    const char *p = format;
    ssize_t res = 0;
    while (true) {
        // first consume everything until a '%%'
        const char *np = strchr(p, '%%');
        size_t skip = np ? np - p : strlen(p);

        if (skip > 0) {
            ssize_t nres = write(ctx, p, skip);
            if (nres < 0) {
                return nres;
            }
            res += nres;
        }

        // hit end of string?
        if (!np) {
            return res;
        }

        // format parser
        p = np;
        bool zero_justify = false;
        bool left_justify = false;
        bool precision_mode = false;
        size_t width = 0;
        size_t precision = 0;

        char mode = 'c';
        uint32_t value = 0;
        size_t size = 0;

        for (;; np++) {
            if (np[1] >= '0' && np[1] <= '9') {
                // precision/width
                if (precision_mode) {
                    precision = precision*10 + (np[1]-'0');
                } else if (np[1] > '0' || width > 0) {
                    width = width*10 + (np[1]-'0');
                } else {
                    zero_justify = true;
                }

            } else if (np[1] == '*') {
                // dynamic precision/width
                if (precision_mode) {
                    precision = va_arg(args, size_t);
                } else {
                    width = va_arg(args, size_t);
                }

            } else if (np[1] == '.') {
                // switch mode
                precision_mode = true;

            } else if (np[1] == '-') {
                // left-justify
                left_justify = true;

            } else if (np[1] == '%%') {
                // single '%%'
                mode = 'c';
                value = '%%';
                size = 1;
                break;

            } else if (np[1] == 'c') {
                // char
                mode = 'c';
                value = va_arg(args, int);
                size = 1;
                break;

            } else if (np[1] == 's') {
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

            } else if (np[1] == 'X' || np[1] == 'x' || np[1] == 'p') {
                // make it prettier for pointers
                if (np[1] == 'p') {
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

            } else if (np[1] == 'd' || np[1] == 'i') {
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

            } else if (np[1] == 'u') {
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

            } else if (np[1] == '\\0') {
                // uh oh
                __box_abort(-1);

            } else {
                // probably an ignored character, skip

            }

        }

        // consume the format
        p = np+2;

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
    // TODO hm, not const?
    return __box_write(1, (void *)buf, size);
}

__attribute__((used))
ssize_t __wrap_vprintf(const char *format, va_list args) {
    return __box_cbprintf(__box_vprintf_write, NULL, format, args);
}

__attribute__((used))
ssize_t __wrap_printf(const char *format, ...) {
    va_list args;
    va_start(args, format);
    ssize_t res = __wrap_vprintf(format, args);
    va_end(args);
    return res;
}
"""

BOX_STDLIB_HOOKS = """
#ifdef __GNUC__
int _write(int handle, char *buffer, int size) {
    return __box_write(handle, (uint8_t*)buffer, size);
}
#endif
"""

class WriteGlue(runtimes.Runtime):
    """
    Helper layer for handling __box_write and friends.
    """
    __name = 'write_glue'
    def box_box(self, box):
        self._write_hook = box.addimport(
            '__box_write', 'fn(i32, u8*, usize) -> errsize',
            target=box.name, source=self.__name, weak=True,
            doc="Provides a minimal implementation of stdout to the box. "
                "The exact behavior depends on the superbox's implementation "
                "of __box_write. If none is provided, __box_write links but "
                "does nothing.")

        super().box_box(box)

    def build_box_c(self, output, box):
        super().build_box_c(output, box)

        output.decls.append('//// __box_write glue ////')
        if not self._write_hook.link:
            # defaults to noop
            out = output.decls.append()
            out.printf('ssize_t __box_write(int32_t fd, '
                'void *buffer, size_t size) {')
            with out.indent():
                out.printf('return size;')
            out.printf('}')
        elif self._write_hook.link.export.alias != '__box_write':
            # jump to correct implementation
            out = output.decls.append()
            out.printf('ssize_t __box_write(int32_t fd, '
                'void *buffer, size_t size) {')
            with out.indent():
                out.printf('return %(alias)s(fd, buffer, size);',
                    alias=self._write_hook.link.export.alias)
            out.printf('}')

        if box.printf == 'minimal':
            output.includes.append('<stdarg.h>')
            output.includes.append('<string.h>')
            out = output.decls.append()
            out.printf(BOX_MINIMAL_PRINTF)

        if box.emit_stdlib_hooks:
            output.decls.append(BOX_STDLIB_HOOKS)

    def build_box_mk(self, output, box):
        super().build_box_mk(output, box)

        if box.emit_stdlib_hooks:
            output.decls.append('### __box_write glue ###')
            output.decls.append('override LFLAGS += -Wl,--wrap,printf')
            output.decls.append('override LFLAGS += -Wl,--wrap,vprintf')
