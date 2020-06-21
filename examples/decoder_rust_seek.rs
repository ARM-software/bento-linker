// Minimal implementation of a GLZ decoder, operates in
// constant RAM and linear time.
//
// Note there are some quirks because the intention is to
// compare with an equivalent C implementation.
//
#[allow(non_camel_case_types)]
type _usize = usize; // workaround until rust v1.43
#[allow(non_camel_case_types)]
type _isize = isize; // workaround until rust v1.43

pub mod glz {
    use std::error;
    use std::fmt;
    use std::cmp;
    use std::io;
    use std::convert::{TryFrom, TryInto};

    // error type
    #[derive(Debug)]
    #[non_exhaustive]
    pub enum Error {
        Inval = -22,
        IO    = -5,
    }

    impl error::Error for Error {}
    impl fmt::Display for Error {
        fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
            match self {
                Self::Inval => write!(f, "Invalid input"),
                Self::IO    => write!(f, "I/O Error"),
            }
        }
    }

    // types used by GLZ, no idea how to do this idiomatically
    // needed to make comparison against C reasonable
    #[allow(non_camel_case_types)]
    pub type usize = ::_usize;
    #[allow(non_camel_case_types)]
    pub type uoff = ::_usize;
    #[allow(non_camel_case_types)]
    pub type ioff = ::_isize;

    // GLZ's M constant (width of reference nibbles)
    const M: usize = 4;

    // GLZ decode logic

    // note we only need these attributes so we can find
    // the compiled size with nm
    #[export_name="glz_decode"]
    #[inline(never)]
    pub fn decode<R: io::Read+io::Seek, W: io::Write>(
        k: u8,
        input: &mut R,
        output: &mut W,
        size: usize,
        off: uoff
    ) -> Result<(), Error> {
        // glz "stack"
        let mut pushed: (usize, uoff) = (0, 0);
        let mut size = size;
        let mut off = off;
        let mut buf = [0u8; 2];

        while size > 0 {
            // decode rice code
            let mut rice: u16 = 0;
            loop {
                input.seek(io::SeekFrom::Start((off/8) as u64))
                    .and_then(|_| input.read_exact(&mut buf[..1]))
                    .map(|_| buf[0] >>= 7-off%8)
                    .map_err(|err| if err.kind() ==
                            io::ErrorKind::UnexpectedEof {
                        Error::Inval
                    } else {
                        Error::IO
                    })?;
                if buf[0] & 1 == 0 {
                    off += 1;
                    break;
                }

                rice += 1;
                off += 1;
            }
            for _ in 0..k {
                input.seek(io::SeekFrom::Start((off/8) as u64))
                    .and_then(|_| input.read_exact(&mut buf[..1]))
                    .map(|_| buf[0] >>= 7-off%8)
                    .map_err(|err| if err.kind() ==
                            io::ErrorKind::UnexpectedEof {
                        Error::Inval
                    } else {
                        Error::IO
                    })?;
                rice = (rice << 1) | u16::from(1 & buf[0]);
                off += 1;
            }

            // map through table
            input.seek(io::SeekFrom::Start((9*uoff::from(rice)/8) as u64))
                .and_then(|_| input.read_exact(&mut buf[..2]))
                .map_err(|err| if err.kind() ==
                        io::ErrorKind::UnexpectedEof {
                    Error::Inval
                } else {
                    Error::IO
                })?;
            let rice = 0x1ff & (
                (u16::from(buf[0]) << 8) |
                (u16::from(buf[1]) << 0)) >> (7-(9*rice)%8);

            // indirect reference or literal?
            if let Ok(rice) = u8::try_from(rice) {
                output.write(&[rice])
                    .map_err(|_| Error::IO)?;
                size -= 1;
            } else {
                let nsize = usize::from(rice & 0xff) + 2;
                let mut noff: uoff = 0;
                loop {
                    let mut n: uoff = 0;
                    for _ in 0..M+1 {
                        input.seek(io::SeekFrom::Start((off/8) as u64))
                            .and_then(|_| input.read_exact(&mut buf[..1]))
                            .map(|_| buf[0] >>= 7-off%8)
                            .map_err(|err| if err.kind() ==
                                    io::ErrorKind::UnexpectedEof {
                                Error::Inval
                            } else {
                                Error::IO
                            })?;
                        n = (n << 1) | uoff::from(1 & buf[0]);
                        off += 1;
                    }

                    noff = (noff << M) + 1 + (n & ((1 << M)-1));
                    if n < (1 << M) {
                        break;
                    }
                }
                noff -= 1;

                // tail recurse?
                if nsize >= size {
                    size = size;
                    off = off + noff;
                } else {
                    pushed = (size - nsize, off);
                    size = nsize;
                    off = off + noff;
                }
            }

            if size == 0 {
                size = pushed.0;
                off = pushed.1;
                pushed = (0, 0);
            }
        }

        Ok(())
    }

    // // helper functions that also decode limited
    // GLZ metadata (size/k/table) from the blob
    // [--  32  --|-  24  -|8][--  ...  --]
    //       ^         ^    ^       ^- compressed blob
    //       |         |    '- k
    //       |         '------ table size in bits
    //       '---------------- size of output blob
    //
    pub fn getsize<R: io::Read+io::Seek>(
        input: &mut R
    ) -> Result<usize, Error> {
        let mut buf = [0u8; 4];
        input.seek(io::SeekFrom::Start(0))
            .and_then(|_| input.read_exact(&mut buf))
            .map_err(|err| if err.kind() == io::ErrorKind::UnexpectedEof {
                Error::Inval
            } else {
                Error::IO
            })?;
        let size = u32::from_le_bytes(buf)
            .try_into().map_err(|_| Error::Inval)?;
        Ok(size)
    }

    pub fn getoff<R: io::Read+io::Seek>(
        input: &mut R
    ) -> Result<uoff, Error> {
        let mut buf = [0u8; 4];
        input.seek(io::SeekFrom::Start(4))
            .and_then(|_| input.read_exact(&mut buf))
            .map_err(|err| if err.kind() == io::ErrorKind::UnexpectedEof {
                Error::Inval
            } else {
                Error::IO
            })?;
        let off = (0x00ffffff & u32::from_le_bytes(buf))
            .try_into().map_err(|_| Error::Inval)?;
        Ok(off)
    }

    pub fn getk<R: io::Read+io::Seek>(
        input: &mut R
    ) -> Result<u8, Error> {
        let mut buf = [0u8; 1];
        input.seek(io::SeekFrom::Start(7))
            .and_then(|_| input.read_exact(&mut buf))
            .map_err(|err| if err.kind() == io::ErrorKind::UnexpectedEof {
                Error::Inval
            } else {
                Error::IO
            })?;
        Ok(buf[0])
    }

    struct ReadSeekSlice<'a, R: io::Read+io::Seek> {
        input: &'a mut R,
        off: ioff,
    }

    impl<R: io::Read+io::Seek> io::Read for ReadSeekSlice<'_, R> {
        fn read(&mut self, buf: &mut [u8]) -> Result<usize, io::Error> {
            self.input.read(buf)
        }
    }

    impl<R: io::Read+io::Seek> io::Seek for ReadSeekSlice<'_, R> {
        fn seek(&mut self, off: io::SeekFrom) -> Result<u64, io::Error> {
            self.input.seek(match off {
                io::SeekFrom::Start(off) => io::SeekFrom::Start(
                    ((off as i64)-(self.off as i64)) as u64),
                off => off,
            })
        }
    }

    pub fn decode_all<R: io::Read+io::Seek, W: io::Write>(
        input: &mut R,
        output: &mut W,
        size: Option<usize>,
    ) -> Result<(), Error> {
        let size = match (getsize(input)?, size) {
            (blob_size, Some(size)) => cmp::min(blob_size, size),
            (blob_size, _) => blob_size,
        };
        let off = getoff(input)?;
        let k = getk(input)?;
        decode(k, &mut ReadSeekSlice{input: input, off: -8}, output, size, off)
    }
    
    pub fn decode_slice<R: io::Read+io::Seek, W: io::Write>(
        input: &mut R,
        output: &mut W,
        size: usize,
        off: uoff
    ) -> Result<(), Error> {
        let k = getk(input)?;
        decode(k, &mut ReadSeekSlice{input: input, off: -8}, output, size, off)
    }
}


// main isn't needed, just presents a CLI for testing/benchmarking
use std::env;
use std::process;
use std::fs;
use std::io;

macro_rules! uparse {
    // need this because how else do we emulate strtol(..., 0)?
    // we can't even use generics here because no common trait for
    // U::from_str_radix
    ($U:ty, $src:expr) => {
        if $src.starts_with("0x") {
            <$U>::from_str_radix(&$src[2..], 16)
        } else {
            <$U>::from_str_radix($src, 10)
        }
    };
}

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() != 2 && args.len() != 4 {
        eprintln!("usage: {} <file> [<size> <offset>]", args[0]);
        process::exit(1);
    }

    // requesting slice?
    let slice = if args.len() == 4 {
        let size = match uparse!(glz::usize, &args[2]) {
            Ok(size) => size,
            _ => {
                eprintln!("bad size \"{}\"?", args[2]);
                process::exit(1);
            }
        };

        let off = match uparse!(glz::uoff, &args[3]) {
            Ok(off) => off,
            _ => {
                eprintln!("bad offset \"{}\"?", args[3]);
                process::exit(1);
            }
        };

        Some((size, off))
    } else {
        None
    };

    // read file
    let mut input = match fs::File::open(&args[1]) {
        Ok(input) => input,
        _ => {
            eprintln!("could not read file \"{}\"?", args[1]);
            process::exit(1);
        }
    };

    // decode!
    match slice {
        Some((size, off)) => {
            match glz::decode_slice(&mut input, &mut io::stdout(), size, off) {
                Ok(_) => {}
                Err(err) => {
                    eprintln!("decode failure ({}) :(", err);
                    process::exit(2);
                }
            }
        }
        _ => {
            match glz::decode_all(&mut input, &mut io::stdout(), None) {
                Ok(_) => {}
                Err(err) => {
                    eprintln!("decode failure ({}) :(", err);
                    process::exit(2);
                }
            }
        }
    }
}
