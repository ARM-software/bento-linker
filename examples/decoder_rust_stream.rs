// Minimal implementation of a GLZ decoder, operates in
// constant RAM and linear time.
//
// Note there are some quirks because the intention is to
// compare with an equivalent C implementation.
//
#[allow(non_camel_case_types)]
type _usize = usize; // workaround until rust v1.43

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

    // GLZ's M constant (width of reference nibbles)
    const M: usize = 4;

    // GLZ decode logic

    // note we only need these attributes so we can find
    // the compiled size with nm
    #[export_name="glz_decode"]
    #[inline(never)]
    pub fn decode<W: io::Write>(
        k: u8,
        blob: &[u8],
        output: &mut W,
        size: usize,
        off: uoff
    ) -> Result<(), Error> {
        // glz "stack"
        let mut pushed: (usize, uoff) = (0, 0);
        let mut size = size;
        let mut off = off;

        while size > 0 {
            // decode rice code
            let mut rice: u16 = 0;
            loop {
                let x = blob.get(off/8)
                    .map(|x| x >> (7-off%8))
                    .ok_or(Error::Inval)?;
                if x & 1 == 0 {
                    off += 1;
                    break;
                }

                rice += 1;
                off += 1;
            }
            for _ in 0..k {
                let x = blob.get(off/8)
                    .map(|x| x >> (7-off%8))
                    .ok_or(Error::Inval)?;
                rice = (rice << 1) | u16::from(1 & x);
                off += 1;
            }

            // map through table
            let rice = match blob.get(
                    (9*uoff::from(rice))/8..(9*uoff::from(rice))/8+2) {
                Some(&[x0, x1]) => {
                    0x1ff & (
                        (u16::from(x0) << 8) |
                        (u16::from(x1) << 0)) >> (7-(9*rice)%8)
                },
                _ => {
                    Err(Error::Inval)?
                },
            };

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
                        let x = blob.get(off/8)
                            .map(|x| x >> (7-off%8))
                            .ok_or(Error::Inval)?;
                        n = (n << 1) | uoff::from(1 & x);
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
    pub fn getsize(blob: &[u8]) -> Result<usize, Error> {
        let buf = blob.get(0..4).ok_or(Error::Inval)?
            .try_into().map_err(|_| Error::Inval)?;
        let size = u32::from_le_bytes(buf)
            .try_into().map_err(|_| Error::Inval)?;
        Ok(size)
    }

    pub fn getoff(blob: &[u8]) -> Result<uoff, Error> {
        let buf = blob.get(4..8).ok_or(Error::Inval)?
            .try_into().map_err(|_| Error::Inval)?;
        let off = (0x00ffffff & u32::from_le_bytes(buf))
            .try_into().map_err(|_| Error::Inval)?;
        Ok(off)
    }

    pub fn getk(blob: &[u8]) -> Result<u8, Error> {
        let k = blob.get(7).ok_or(Error::Inval)?;
        Ok(*k)
    }

    pub fn decode_all<W: io::Write>(
        blob: &[u8],
        output: &mut W,
        size: Option<usize>,
    ) -> Result<(), Error> {
        let size = match (getsize(blob)?, size) {
            (blob_size, Some(size)) => cmp::min(blob_size, size),
            (blob_size, _) => blob_size,
        };
        let off = getoff(blob)?;
        let k = getk(blob)?;
        let blob = blob.get(8..).ok_or(Error::Inval)?;
        decode(k, blob, output, size, off)
    }
    
    pub fn decode_slice<W: io::Write>(
        blob: &[u8],
        output: &mut W,
        size: usize,
        off: uoff
    ) -> Result<(), Error> {
        let k = getk(blob)?;
        let blob = blob.get(8..).ok_or(Error::Inval)?;
        decode(k, blob, output, size, off)
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
    let blob = match fs::read(&args[1]) {
        Ok(input) => input,
        _ => {
            eprintln!("could not read file \"{}\"?", args[1]);
            process::exit(1);
        }
    };

    // decode!
    match slice {
        Some((size, off)) => {
            match glz::decode_slice(&blob, &mut io::stdout(), size, off) {
                Ok(_) => {}
                Err(err) => {
                    eprintln!("decode failure ({}) :(", err);
                    process::exit(2);
                }
            }
        }
        _ => {
            match glz::decode_all(&blob, &mut io::stdout(), None) {
                Ok(_) => {}
                Err(err) => {
                    eprintln!("decode failure ({}) :(", err);
                    process::exit(2);
                }
            }
        }
    }
}
