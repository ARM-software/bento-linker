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
    # name               prefix-less name  code  description
    ('OK',              'OK',              0,   'No error'),
    ('GENERAL',         'GENERAL',         1,   'General error'),
    ('NOENT',           'NOENT',           2,   'No such file or directory'),
    ('SRCH',            'SRCH',            3,   'No such process'),
    ('INTR',            'INTR',            4,   'Interrupted system call'),
    ('IO',              'IO',              5,   'I/O error'),
    ('NXIO',            'NXIO',            6,   'No such device or address'),
    ('2BIG',            'TOOBIG',         7,   'Argument list too long'),
    ('NOEXEC',          'NOEXEC',          8,   'Exec format error'),
    ('BADF',            'BADF',            9,   'Bad file number'),
    ('CHILD',           'CHILD',           10,  'No child processes'),
    ('AGAIN',           'AGAIN',           11,  'Try again'),
    ('NOMEM',           'NOMEM',           12,  'Out of memory'),
    ('ACCES',           'ACCES',           13,  'Permission denied'),
    ('FAULT',           'FAULT',           14,  'Bad address'),
    ('BUSY',            'BUSY',            16,  'Device or resource busy'),
    ('EXIST',           'EXIST',           17,  'File exists'),
    ('XDEV',            'XDEV',            18,  'Cross-device link'),
    ('NODEV',           'NODEV',           19,  'No such device'),
    ('NOTDIR',          'NOTDIR',          20,  'Not a directory'),
    ('ISDIR',           'ISDIR',           21,  'Is a directory'),
    ('INVAL',           'INVAL',           22,  'Invalid argument'),
    ('NFILE',           'NFILE',           23,  'File table overflow'),
    ('MFILE',           'MFILE',           24,  'Too many open files'),
    ('NOTTY',           'NOTTY',           25,  'Not a typewriter'),
    ('TXTBSY',          'TXTBSY',          26,  'Text file busy'),
    ('FBIG',            'FBIG',            27,  'File too large'),
    ('NOSPC',           'NOSPC',           28,  'No space left on device'),
    ('SPIPE',           'SPIPE',           29,  'Illegal seek'),
    ('ROFS',            'ROFS',            30,  'Read-only file system'),
    ('MLINK',           'MLINK',           31,  'Too many links'),
    ('PIPE',            'PIPE',            32,  'Broken pipe'),
    ('DOM',             'DOM',             33,  'Math argument out of domain of func'),
    ('RANGE',           'RANGE',           34,  'Math result not representable'),
    ('DEADLK',          'DEADLK',          35,  'Resource deadlock would occur'),
    ('NAMETOOLONG',     'NAMETOOLONG',     36,  'File name too long'),
    ('NOLCK',           'NOLCK',           37,  'No record locks available'),
    ('NOSYS',           'NOSYS',           38,  'Function not implemented'),
    ('NOTEMPTY',        'NOTEMPTY',        39,  'Directory not empty'),
    ('LOOP',            'LOOP',            40,  'Too many symbolic links encountered'),
    ('NOMSG',           'NOMSG',           42,  'No message of desired type'),
    ('IDRM',            'IDRM',            43,  'Identifier removed'),
    ('NOSTR',           'NOSTR',           60,  'Device not a stream'),
    ('NODATA',          'NODATA',          61,  'No data available'),
    ('TIME',            'TIME',            62,  'Timer expired'),
    ('NOSR',            'NOSR',            63,  'Out of streams resources'),
    ('NOLINK',          'NOLINK',          67,  'Link has been severed'),
    ('PROTO',           'PROTO',           71,  'Protocol error'),
    ('MULTIHOP',        'MULTIHOP',        72,  'Multihop attempted'),
    ('BADMSG',          'BADMSG',          74,  'Not a data message'),
    ('OVERFLOW',        'OVERFLOW',        75,  'Value too large for defined data type'),
    ('ILSEQ',           'ILSEQ',           84,  'Illegal byte sequence'),
    ('NOTSOCK',         'NOTSOCK',         88,  'Socket operation on non-socket'),
    ('DESTADDRREQ',     'DESTADDRREQ',     89,  'Destination address required'),
    ('MSGSIZE',         'MSGSIZE',         90,  'Message too long'),
    ('PROTOTYPE',       'PROTOTYPE',       91,  'Protocol wrong type for socket'),
    ('NOPROTOOPT',      'NOPROTOOPT',      92,  'Protocol not available'),
    ('PROTONOSUPPORT',  'PROTONOSUPPORT',  93,  'Protocol not supported'),
    ('OPNOTSUPP',       'OPNOTSUPP',       95,  'Operation not supported on transport endpoint'),
    ('AFNOSUPPORT',     'AFNOSUPPORT',     97,  'Address family not supported by protocol'),
    ('ADDRINUSE',       'ADDRINUSE',       98,  'Address already in use'),
    ('ADDRNOTAVAIL',    'ADDRNOTAVAIL',    99,  'Cannot assign requested address'),
    ('NETDOWN',         'NETDOWN',         100, 'Network is down'),
    ('NETUNREACH',      'NETUNREACH',      101, 'Network is unreachable'),
    ('NETRESET',        'NETRESET',        102, 'Network dropped connection because of reset'),
    ('CONNABORTED',     'CONNABORTED',     103, 'Software caused connection abort'),
    ('CONNRESET',       'CONNRESET',       104, 'Connection reset by peer'),
    ('NOBUFS',          'NOBUFS',          105, 'No buffer space available'),
    ('ISCONN',          'ISCONN',          106, 'Transport endpoint is already connected'),
    ('NOTCONN',         'NOTCONN',         107, 'Transport endpoint is not connected'),
    ('TIMEDOUT',        'TIMEDOUT',        110, 'Connection timed out'),
    ('CONNREFUSED',     'CONNREFUSED',     111, 'Connection refused'),
    ('HOSTUNREACH',     'HOSTUNREACH',     113, 'No route to host'),
    ('ALREADY',         'ALREADY',         114, 'Operation already in progress'),
    ('INPROGRESS',      'INPROGRESS',      115, 'Operation now in progress'),
    ('STALE',           'STALE',           116, 'Stale NFS file handle'),
    ('DQUOT',           'DQUOT',           122, 'Quota exceeded'),
    ('CANCELED',        'CANCELED',        125, 'Operation Canceled'),
    ('OWNERDEAD',       'OWNERDEAD',       130, 'Owner died'),
    ('NOTRECOVERABLE',  'NOTRECOVERABLE',  131, 'State not recoverable'),
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
        Self::GENERAL
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
    def build_c_prologue_common(self, output, box):

        out = output.decls.append()
        out.printf('//// box error codes ////')
        out.printf('enum box_errors {')
        # TODO configurable prefixes?
        with out.indent():
            for name, _, code, doc in ERRORS:
                out.printf('E%(name)-16s = %(code)-5s // %(doc)s',
                    name=name,
                    code='%d,' % code,
                    doc=doc)
        out.printf('};')

    def build_h_prologue(self, output, box):
        super().build_h_prologue(output, box)
        self.build_c_prologue_common(output, box)

    def build_c_prologue(self, output, box):
        super().build_c_prologue(output, box)
        self.build_c_prologue_common(output, box)

    def build_rs_prologue(self, output, box):
        super().build_rs_prologue(output, box)
        # TODO use proper casing?

        output.uses.append('core::num')
        output.uses.append('core::convert::TryFrom')
        output.decls.append(RUST_ERROR_STRUCT)
        output.decls.append(RUST_ERROR_IMPL)

        out = output.decls.append()
        out.printf('impl Error {')
        with out.indent():
            for _, name, code, doc in ERRORS[1:]:
                # TODO can these be one line?
                out.printf('/// %(doc)s',
                    doc=doc)
                out.printf('pub const %(name)-16s '
                        ': Error = unsafe { Error::new_unchecked(%(code)d) };',
                    name=name,
                    code=code)
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




