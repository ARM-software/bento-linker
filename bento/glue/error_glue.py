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
    # name               rust name         code  description
    ('OK',              'Ok',              0,   'No error'),
    ('GENERAL',         'General',         1,   'General error'),
    ('NOENT',           'NoEnt',           2,   'No such file or directory'),
    ('SRCH',            'Srch',            3,   'No such process'),
    ('INTR',            'Intr',            4,   'Interrupted system call'),
    ('IO',              'Io',              5,   'I/O error'),
    ('NXIO',            'NXIo',            6,   'No such device or address'),
    ('2BIG',            'TooBig',          7,   'Argument list too long'),
    ('NOEXEC',          'NoExec',          8,   'Exec format error'),
    ('BADF',            'BadF',            9,   'Bad file number'),
    ('CHILD',           'Child',           10,  'No child processes'),
    ('AGAIN',           'Again',           11,  'Try again'),
    ('NOMEM',           'NoMem',           12,  'Out of memory'),
    ('ACCES',           'Acces',           13,  'Permission denied'),
    ('FAULT',           'Fault',           14,  'Bad address'),
    ('BUSY',            'Busy',            16,  'Device or resource busy'),
    ('EXIST',           'Exist',           17,  'File exists'),
    ('XDEV',            'XDev',            18,  'Cross-device link'),
    ('NODEV',           'NoDev',           19,  'No such device'),
    ('NOTDIR',          'NotDir',          20,  'Not a directory'),
    ('ISDIR',           'IsDir',           21,  'Is a directory'),
    ('INVAL',           'Inval',           22,  'Invalid argument'),
    ('NFILE',           'NFile',           23,  'File table overflow'),
    ('MFILE',           'MFile',           24,  'Too many open files'),
    ('NOTTY',           'NoTty',           25,  'Not a typewriter'),
    ('TXTBSY',          'TxtBsy',          26,  'Text file busy'),
    ('FBIG',            'FBig',            27,  'File too large'),
    ('NOSPC',           'NoSpc',           28,  'No space left on device'),
    ('SPIPE',           'SPipe',           29,  'Illegal seek'),
    ('ROFS',            'RoFs',            30,  'Read-only file system'),
    ('MLINK',           'MLink',           31,  'Too many links'),
    ('PIPE',            'Pipe',            32,  'Broken pipe'),
    ('DOM',             'Dom',             33,  'Math argument out of domain of func'),
    ('RANGE',           'Range',           34,  'Math result not representable'),
    ('DEADLK',          'DeadLk',          35,  'Resource deadlock would occur'),
    ('NAMETOOLONG',     'NameTooLong',     36,  'File name too long'),
    ('NOLCK',           'NoLck',           37,  'No record locks available'),
    ('NOSYS',           'NoSys',           38,  'Function not implemented'),
    ('NOTEMPTY',        'NotEmpty',        39,  'Directory not empty'),
    ('LOOP',            'Loop',            40,  'Too many symbolic links encountered'),
    ('NOMSG',           'NoMsg',           42,  'No message of desired type'),
    ('IDRM',            'IdRm',            43,  'Identifier removed'),
    ('NOSTR',           'NoStr',           60,  'Device not a stream'),
    ('NODATA',          'NoData',          61,  'No data available'),
    ('TIME',            'Time',            62,  'Timer expired'),
    ('NOSR',            'NoSr',            63,  'Out of streams resources'),
    ('NOLINK',          'NoLink',          67,  'Link has been severed'),
    ('PROTO',           'Proto',           71,  'Protocol error'),
    ('MULTIHOP',        'Multihop',        72,  'Multihop attempted'),
    ('BADMSG',          'BadMsg',          74,  'Not a data message'),
    ('OVERFLOW',        'Overflow',        75,  'Value too large for defined data type'),
    ('ILSEQ',           'IlSeq',           84,  'Illegal byte sequence'),
    ('NOTSOCK',         'NotSock',         88,  'Socket operation on non-socket'),
    ('DESTADDRREQ',     'DestAddrReq',     89,  'Destination address required'),
    ('MSGSIZE',         'MsgSize',         90,  'Message too long'),
    ('PROTOTYPE',       'Prototype',       91,  'Protocol wrong type for socket'),
    ('NOPROTOOPT',      'NoProtoOpt',      92,  'Protocol not available'),
    ('PROTONOSUPPORT',  'ProtoNoSupport',  93,  'Protocol not supported'),
    ('OPNOTSUPP',       'OpNotSupp',       95,  'Operation not supported on transport endpoint'),
    ('AFNOSUPPORT',     'AfNoSupport',     97,  'Address family not supported by protocol'),
    ('ADDRINUSE',       'AddrInUse',       98,  'Address already in use'),
    ('ADDRNOTAVAIL',    'AddrNotAvail',    99,  'Cannot assign requested address'),
    ('NETDOWN',         'NetDown',         100, 'Network is down'),
    ('NETUNREACH',      'NetUnreach',      101, 'Network is unreachable'),
    ('NETRESET',        'NetReset',        102, 'Network dropped connection because of reset'),
    ('CONNABORTED',     'ConnAborted',     103, 'Software caused connection abort'),
    ('CONNRESET',       'ConnReset',       104, 'Connection reset by peer'),
    ('NOBUFS',          'NoBufs',          105, 'No buffer space available'),
    ('ISCONN',          'IsConn',          106, 'Transport endpoint is already connected'),
    ('NOTCONN',         'NotConn',         107, 'Transport endpoint is not connected'),
    ('TIMEDOUT',        'TimedOut',        110, 'Connection timed out'),
    ('CONNREFUSED',     'ConnRefused',     111, 'Connection refused'),
    ('HOSTUNREACH',     'HostUnreach',     113, 'No route to host'),
    ('ALREADY',         'Already',         114, 'Operation already in progress'),
    ('INPROGRESS',      'InProgress',      115, 'Operation now in progress'),
    ('STALE',           'Stale',           116, 'Stale NFS file handle'),
    ('DQUOT',           'DQuot',           122, 'Quota exceeded'),
    ('CANCELED',        'Canceled',        125, 'Operation Canceled'),
    ('OWNERDEAD',       'OwnerDead',       130, 'Owner died'),
    ('NOTRECOVERABLE',  'NotRecoverable',  131, 'State not recoverable'),
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




