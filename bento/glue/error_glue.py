from .. import glue

"""
Set of error codes that can be shared across boxes. This is
derived from the common POSIX error codes.

There are quirks from using POSIX as a base, but relying on
the history here offers a better chance to capture most error
conditions better than fabricating a new set.

Note that when returned from import/exports, error codes are
negated to allow the positive integer range to be used for
successful results.

Two notes:
1. Error codes > 256 can be used for non-standard, library
   specific errors. No rules drive these.

2. Error -1 is repurposed to indicate a "general error", an
   error code with no specific code assigned. This is to help
   integrate with libraries that return -1 which is common.

The error code set is limited to official POSIX error codes, but
the encoding is based on Linux due to common OS extensions
intersperesed in the encoding:
https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/errno.h.html
"""

ERRORS = [
    # name              rust name          code description
    ('EOK',             'Ok',              0,   'No error'),
    ('EGENERAL',        'General',         1,   'General error'),
    ('ENOENT',          'NoEnt',           2,   'No such file or directory'),
    ('ESRCH',           'Srch',            3,   'No such process'),
    ('EINTR',           'Intr',            4,   'Interrupted system call'),
    ('EIO',             'Io',              5,   'I/O error'),
    ('ENXIO',           'NXIo',            6,   'No such device or address'),
    ('E2BIG',           'TooBig',          7,   'Argument list too long'),
    ('ENOEXEC',         'NoExec',          8,   'Exec format error'),
    ('EBADF',           'BadF',            9,   'Bad file number'),
    ('ECHILD',          'Child',           10,  'No child processes'),
    ('EAGAIN',          'Again',           11,  'Try again'),
    ('ENOMEM',          'NoMem',           12,  'Out of memory'),
    ('EACCES',          'Acces',           13,  'Permission denied'),
    ('EFAULT',          'Fault',           14,  'Bad address'),
    ('EBUSY',           'Busy',            16,  'Device or resource busy'),
    ('EEXIST',          'Exist',           17,  'File exists'),
    ('EXDEV',           'XDev',            18,  'Cross-device link'),
    ('ENODEV',          'NoDev',           19,  'No such device'),
    ('ENOTDIR',         'NotDir',          20,  'Not a directory'),
    ('EISDIR',          'IsDir',           21,  'Is a directory'),
    ('EINVAL',          'Inval',           22,  'Invalid argument'),
    ('ENFILE',          'NFile',           23,  'File table overflow'),
    ('EMFILE',          'MFile',           24,  'Too many open files'),
    ('ENOTTY',          'NoTty',           25,  'Not a typewriter'),
    ('ETXTBSY',         'TxtBsy',          26,  'Text file busy'),
    ('EFBIG',           'FBig',            27,  'File too large'),
    ('ENOSPC',          'NoSpc',           28,  'No space left on device'),
    ('ESPIPE',          'SPipe',           29,  'Illegal seek'),
    ('EROFS',           'RoFs',            30,  'Read-only file system'),
    ('EMLINK',          'MLink',           31,  'Too many links'),
    ('EPIPE',           'Pipe',            32,  'Broken pipe'),
    ('EDOM',            'Dom',             33,  'Math argument out of domain of func'),
    ('ERANGE',          'Range',           34,  'Math result not representable'),
    ('EDEADLK',         'DeadLk',          35,  'Resource deadlock would occur'),
    ('ENAMETOOLONG',    'NameTooLong',     36,  'File name too long'),
    ('ENOLCK',          'NoLck',           37,  'No record locks available'),
    ('ENOSYS',          'NoSys',           38,  'Function not implemented'),
    ('ENOTEMPTY',       'NotEmpty',        39,  'Directory not empty'),
    ('ELOOP',           'Loop',            40,  'Too many symbolic links encountered'),
    ('ENOMSG',          'NoMsg',           42,  'No message of desired type'),
    ('EIDRM',           'IdRm',            43,  'Identifier removed'),
    ('ENOSTR',          'NoStr',           60,  'Device not a stream'),
    ('ENODATA',         'NoData',          61,  'No data available'),
    ('ETIME',           'Time',            62,  'Timer expired'),
    ('ENOSR',           'NoSr',            63,  'Out of streams resources'),
    ('ENOLINK',         'NoLink',          67,  'Link has been severed'),
    ('EPROTO',          'Proto',           71,  'Protocol error'),
    ('EMULTIHOP',       'Multihop',        72,  'Multihop attempted'),
    ('EBADMSG',         'BadMsg',          74,  'Not a data message'),
    ('EOVERFLOW',       'Overflow',        75,  'Value too large for defined data type'),
    ('EILSEQ',          'IlSeq',           84,  'Illegal byte sequence'),
    ('ENOTSOCK',        'NotSock',         88,  'Socket operation on non-socket'),
    ('EDESTADDRREQ',    'DestAddrReq',     89,  'Destination address required'),
    ('EMSGSIZE',        'MsgSize',         90,  'Message too long'),
    ('EPROTOTYPE',      'Prototype',       91,  'Protocol wrong type for socket'),
    ('ENOPROTOOPT',     'NoProtoOpt',      92,  'Protocol not available'),
    ('EPROTONOSUPPORT', 'ProtoNoSupport',  93,  'Protocol not supported'),
    ('EOPNOTSUPP',      'OpNotSupp',       95,  'Operation not supported on transport endpoint'),
    ('EAFNOSUPPORT',    'AfNoSupport',     97,  'Address family not supported by protocol'),
    ('EADDRINUSE',      'AddrInUse',       98,  'Address already in use'),
    ('EADDRNOTAVAIL',   'AddrNotAvail',    99,  'Cannot assign requested address'),
    ('ENETDOWN',        'NetDown',         100, 'Network is down'),
    ('ENETUNREACH',     'NetUnreach',      101, 'Network is unreachable'),
    ('ENETRESET',       'NetReset',        102, 'Network dropped connection because of reset'),
    ('ECONNABORTED',    'ConnAborted',     103, 'Software caused connection abort'),
    ('ECONNRESET',      'ConnReset',       104, 'Connection reset by peer'),
    ('ENOBUFS',         'NoBufs',          105, 'No buffer space available'),
    ('EISCONN',         'IsConn',          106, 'Transport endpoint is already connected'),
    ('ENOTCONN',        'NotConn',         107, 'Transport endpoint is not connected'),
    ('ETIMEDOUT',       'TimedOut',        110, 'Connection timed out'),
    ('ECONNREFUSED',    'ConnRefused',     111, 'Connection refused'),
    ('EHOSTUNREACH',    'HostUnreach',     113, 'No route to host'),
    ('EALREADY',        'Already',         114, 'Operation already in progress'),
    ('EINPROGRESS',     'InProgress',      115, 'Operation now in progress'),
    ('ESTALE',          'Stale',           116, 'Stale NFS file handle'),
    ('EDQUOT',          'DQuot',           122, 'Quota exceeded'),
    ('ECANCELED',       'Canceled',        125, 'Operation Canceled'),
    ('EOWNERDEAD',      'OwnerDead',       130, 'Owner died'),
    ('ENOTRECOVERABLE', 'NotRecoverable',  131, 'State not recoverable'),
]

RUST_ERROR_STRUCT = '''
/// Error type, internally wraps a u31
#[derive(Copy, Clone, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub struct Error(num::NonZeroU32);
'''

RUST_ERROR_IMPL = '''
impl Error {
    pub const unsafe fn new_unchecked(code: u32) -> Self {
        Self(num::NonZeroU32::new_unchecked(code))
    }

    pub fn new(code: u32) -> Option<Self> {
        if code < 2u32.pow(31) {
            Some(Self(num::NonZeroU32::new(code)?))
        } else {
            None
        }
    }

    pub const fn get(self) -> u32 {
        self.0.get()
    }

    /// Error codes are 31-bit values, so we can convert to
    /// an i32 safely
    pub const fn get_i32(self) -> i32 {
        self.0.get() as i32
    }
}

impl Default for Error {
    fn default() -> Self {
        Self::General
    }
}
'''

RUST_RESULT_TYPE = '''
pub type Result<T> = result::Result<T, Error>;
'''

class ErrorGlue(glue.Glue):
    """
    Helper layer for generating error codes in different languages.
    """
    __name = 'error_glue'

    @staticmethod
    def errors():
        """ Iterate over errors """
        return ((name, code, desc) for name, _, code, desc in ERRORS)

    @staticmethod
    def geterror(error):
        """ Look up errors via name or number """
        if isinstance(error, int):
            # code?
            if error < 0:
                error = -error
            for name, _, code, desc in ERRORS:
                if code == error:
                    return (name, code, desc)
        else:
            # name?
            for name, _, code, desc in ERRORS:
                if name == error:
                    return (name, code, desc)
            # Rust name?
            if error.startswith('Error::'):
                error = error[len('Error::'):]
            for name, rustname, code, desc in ERRORS:
                if rustname == error:
                    return (name, code, desc)

    def __build_common_prologue(self, output, box):
        out = output.decls.append()
        out.printf('//// box error codes ////')
        out.printf('enum box_errors {')
        with out.indent():
            for name, _, code, doc in ERRORS:
                out.printf('%(name)-16s = %(code)-5s // %(doc)s',
                    name=name,
                    code='%d,' % code,
                    doc=doc)
        out.printf('};')

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

    def __build_common_rust_lib_prologue(self, output, box):
        output.uses.append('core::num')
        output.decls.append(RUST_ERROR_STRUCT)
        output.decls.append(RUST_ERROR_IMPL)

        out = output.decls.append()
        out.printf('impl Error {')
        with out.indent():
            for _, name, code, doc in ERRORS[1:]:
                with out.pushattrs(
                        name=name,
                        code=code,
                        doc=doc):
                    out.printf('/// %(doc)s')
                    # we're emulating enums here, which is what the user
                    # expects...
                    out.printf('#[allow(non_upper_case_globals)]')
                    out.printf('pub const %(name)-16s : Error\n'
                        '    = unsafe { Error::new_unchecked(%(code)d) };')
            out.printf()
        out.printf('}')

        output.uses.append('core::fmt')
        out = output.decls.append()
        out.printf('impl fmt::Display for Error {')
        with out.indent():
            out.printf('fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {')
            with out.indent():
                out.printf('match *self {')
                with out.indent():
                    for _, name, code, doc in ERRORS[1:]:
                        out.printf('Error::%(name)-16s => '
                            'write!(f, "%(doc)s"),',
                            name=name,
                            doc=doc)
                    out.printf('_%()22s => write!(f, "Error {}", self.get()),')
                out.printf('}')
            out.printf('}')
        out.printf('}')

        output.uses.append('core::result')
        output.decls.append(RUST_RESULT_TYPE)

    def build_rust_lib_prologue(self, output, box):
        super().build_rust_lib_prologue(output, box)
        self.__build_common_rust_lib_prologue(output, box)

    def build_wasm_rust_lib_prologue(self, output, box):
        super().build_wasm_rust_lib_prologue(output, box)
        self.__build_common_rust_lib_prologue(output, box)

