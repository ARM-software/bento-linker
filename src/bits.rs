use crate::errors::*;

use std::convert::TryFrom;
use std::hash;
use std::mem;
use std::fmt::Debug;

use error_chain::ensure;

pub use bitvec::prelude::*;


// Symbols that can be encoded (u8, u16, u32)
// Note these can all be expanded to u32
pub trait Sym
where
    Self: TryFrom<u32> + Into<u32>,
    Self: CastNonsense<u32> + CastNonsense<usize>,
    Self: Copy + Default,
    Self: Eq + hash::Hash + Ord,
    Self: Debug,
{
    fn encode_sym(width: usize, n: Self) -> Result<BitVec>;
    fn decode_sym(width: usize, bits: &BitSlice) -> Result<Self>;

    fn cast<U: Sym>(n: U) -> Result<Self> {
        Ok(Self::cast_nonsense(n.into())?)
    }
}

fn ensure_width<U: Sym>(width: usize, n: Option<u32>, op: &str) -> Result<()> {
    let realwidth = 8*mem::size_of::<U>();
    ensure!(width <= realwidth,
        "attempted to {} {}-bit symbol as u{}",
        op, width, realwidth);
    if let Some(n) = n {
        ensure!(width >= 32 || n < 2u32.pow(width as u32),
            "{} would overflow a {}-bit symbol", op, width);
    }
    Ok(())
}

macro_rules! ensure_width {
    ($u:ty, $width:expr, $op:expr) => {
        ensure_width::<$u>($width, None, $op)?
    };

    ($u:ty, $width:expr, $n:expr, $op:expr) => {
        ensure_width::<$u>($width, Some(u32::cast($n)?), $op)?
    };
}

fn encode_sym<U: Sym>(width: usize, n: U) -> Result<BitVec> {
    Ok(u32::cast(n)?.as_bitslice::<BigEndian>()[32-width..].iter().collect())
}

fn decode_sym<U: Sym>(width: usize, bits: &BitSlice) -> Result<U> {
    ensure!(bits.len() >= width, "found truncated {}-bit symbol", width);

    U::cast(bits[..width].iter().enumerate().fold(0, |s, (i, v)| {
        s | ((v as u32) << ((width - i - 1) as u32))
    }))
}

impl Sym for u8 {
    fn encode_sym(width: usize, n: u8) -> Result<BitVec> {
        ensure_width!(u8, width, n, "encode");
        Ok(BitVec::from_bitslice(&n.as_bitslice::<BigEndian>()[8-width..]))
    }

    fn decode_sym(width: usize, bits: &BitSlice) -> Result<u8> {
        ensure_width!(u8, width, "decode");
        decode_sym(width, bits)
    }
}

impl Sym for u16 {
    fn encode_sym(width: usize, n: u16) -> Result<BitVec> {
        ensure_width!(u16, width, n, "encode");
        encode_sym(width, n)
    }

    fn decode_sym(width: usize, bits: &BitSlice) -> Result<u16> {
        ensure_width!(u16, width, "decode");
        decode_sym(width, bits)
    }
}

impl Sym for u32 {
    fn encode_sym(width: usize, n: u32) -> Result<BitVec> {
        ensure_width!(u32, width, n, "encode");
        encode_sym(width, n)
    }

    fn decode_sym(width: usize, bits: &BitSlice) -> Result<u32> {
        ensure_width!(u32, width, "decode");
        decode_sym(width, bits)
    }
}

macro_rules! mkrule {
    ($name:ident { $target:ident($u:ty$(, $x:ident: $xt:ty)*) }) => {
        fn $name(&self, n: $u$(, $x: $xt)*) -> Result<BitVec> {
            self.$target(n$(, $x)*)
        }
    };

    ($name:ident { $target:ident($($x:ident: $xt:ty),*) -> $u:ty }) => {
        fn $name(&self, bits: &BitSlice$(, $x: $xt)*) -> Result<$u> {
            self.$target(bits$(, $x)*)
        }
    };
}

// Generalized encoder, operates on streams of symbols
pub trait Encode {
    fn encode<U: Sym>(&self, bytes: &[U]) -> Result<BitVec> {
        self.encode_with_prog(bytes, |_|())
    }

    fn decode<U: Sym>(&self, bits: &BitSlice) -> Result<Vec<U>> {
        self.decode_with_prog(bits, |_|())
    }

    fn encode_with_prog<U: Sym>(
        &self,
        bytes: &[U],
        prog: impl FnMut(usize),
    ) -> Result<BitVec>;

    fn decode_with_prog<U: Sym>(
        &self,
        bits: &BitSlice,
        prog: impl FnMut(usize),
    ) -> Result<Vec<U>>;
}

// Symbol encoder, operates on variable sized symbols
pub trait SymEncode {
    fn encode_sym<U: Sym>(&self, n: U) -> Result<BitVec>;
    fn decode_sym<U: Sym>(&self, bits: &BitSlice) -> Result<(U, usize)>;

    fn decode_sym_at<U: Sym>(
        &self,
        bits: &BitSlice,
        off: usize
    ) -> Result<(U, usize)> {
        self.decode_sym(&bits[off..])
    }

    mkrule!(encode_u8  { encode_sym(u8)  });
    mkrule!(encode_u16 { encode_sym(u16) });
    mkrule!(encode_u32 { encode_sym(u32) });
    mkrule!(decode_u8  { decode_sym() -> (u8,  usize) });
    mkrule!(decode_u16 { decode_sym() -> (u16, usize) });
    mkrule!(decode_u32 { decode_sym() -> (u32, usize) });

    mkrule!(decode_u8_at    { decode_sym_at(off: usize) -> (u8,  usize) });
    mkrule!(decode_u16_at   { decode_sym_at(off: usize) -> (u16, usize) });
    mkrule!(decode_u32_at   { decode_sym_at(off: usize) -> (u32, usize) });
}

// All symbol encoders are encoders
impl<T: SymEncode> Encode for T {
    fn encode_with_prog<U: Sym>(
        &self,
        bytes: &[U],
        mut prog: impl FnMut(usize),
    ) -> Result<BitVec> {
        Ok(bytes.iter()
            .map(|&n| {
                let n = self.encode_sym(n);
                prog(1);
                n
            })
            .collect::<Result<Vec<_>>>()?
            .into_iter().flatten()
            .collect())
    }

    fn decode_with_prog<U: Sym>(
        &self,
        bits: &BitSlice,
        mut prog: impl FnMut(usize)
    ) -> Result<Vec<U>> {
        let mut words: Vec<U> = Vec::new();
        let mut off = 0;
        while off < bits.len() {
            let (n, diff) = self.decode_sym_at(bits, off)?;
            words.push(n);
            prog(1);
            off += diff;
        }
        Ok(words)
    }
}

pub trait GranularEncode {
    fn encode_all<U: Sym>(
        &self,
        slices: &[&[U]]
    ) -> Result<(BitVec, Vec<(usize, usize)>)> {
        self.encode_all_with_prog(slices, (|_|(), |_|()))
    }

    fn decode_all<U: Sym>(
        &self,
        bits: &BitSlice,
        offs: &[(usize, usize)]
    ) -> Result<Vec<Vec<U>>> {
        self.decode_all_with_prog(bits, offs, (|_|(), |_|()))
    }

    fn decode_at<U: Sym>(
        &self,
        bits: &BitSlice,
        off: usize,
        len: usize
    ) -> Result<Vec<U>> {
        self.decode_at_with_prog(bits, off, len, |_|())
    }

    fn encode_all_with_prog<U: Sym>(
        &self,
        slices: &[&[U]],
        prog: (impl FnMut(usize), impl FnMut(usize)),
    ) -> Result<(BitVec, Vec<(usize, usize)>)>;

    fn decode_all_with_prog<U: Sym>(
        &self,
        bits: &BitSlice,
        offs: &[(usize, usize)],
        mut prog: (impl FnMut(usize), impl FnMut(usize)),
    ) -> Result<Vec<Vec<U>>> {
        offs.iter().map(|(off, len)| {
            let slice = self.decode_at_with_prog(bits, *off, *len, &mut prog.1);
            prog.0(1);
            slice
        }).collect()
    }

    fn decode_at_with_prog<U: Sym>(
        &self,
        bits: &BitSlice,
        off: usize,
        len: usize,
        prog: impl FnMut(usize),
    ) -> Result<Vec<U>>;
}

impl<T: SymEncode> GranularEncode for T {
    fn encode_all_with_prog<U: Sym>(
        &self,
        slices: &[&[U]],
        mut prog: (impl FnMut(usize), impl FnMut(usize)),
    ) -> Result<(BitVec, Vec<(usize, usize)>)> {
        let bits = slices.iter()
            .rev()
            .map(|slice| {
                let slice = self.encode_with_prog(slice, &mut prog.1);
                prog.0(1);
                slice
            })
            .collect::<Result<Vec<_>>>()?;

        let mut off = 0;
        Ok((
            bits.iter().flatten().collect(),
            bits.iter().zip(slices).map(|(bits, slice)| {
                off += bits.len();
                (off-bits.len(), slice.len())
            }).collect()
        ))
    }

    fn decode_at_with_prog<U: Sym>(
        &self,
        bits: &BitSlice,
        off: usize,
        len: usize,
        mut prog: impl FnMut(usize),
    ) -> Result<Vec<U>> {
        let mut words = Vec::new();
        let mut off = off;
        while words.len() < len {
            let (n, diff) = self.decode_sym_at(bits, off)?;
            words.push(n);
            prog(diff);
            off += diff;
        }
        Ok(words)
    }
}

// A usize value can be a symbol encoder (fixed width integers)
impl SymEncode for usize {
    fn encode_sym<U: Sym>(&self, n: U) -> Result<BitVec> {
        U::encode_sym(*self, n)
    }

    fn decode_sym<U: Sym>(&self, bits: &BitSlice) -> Result<(U, usize)> {
        U::decode_sym(*self, bits).map(|v| (v, *self))
    }
}


#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn encode_test() -> Result<()> {
        assert_eq!(
            8.encode_u8(0b11001001u8)?,
            bitvec![1,1,0,0,1,0,0,1]
        );
        Ok(())
    }

    #[test]
    fn decode_test() -> Result<()> {
        assert_eq!(
            8.decode_u8(&bitvec![1,1,0,0,1,0,0,1])?,
            (0b11001001u8, 8)
        );
        Ok(())
    }

    #[test]
    fn errors_test() -> Result<()> {
        assert!(
            16.encode_u8(0b11001001u8)
                .is_err()
        );
        assert!(
            8.encode_u16(0b1100100100000000u16)
                .is_err()
        );
        assert!(
            16.decode_u8(&bitvec![1,1,0,0,1,0,0,1,0,0,0,0,0,0,0,0])
                .is_err()
        );
        assert!(
            16.decode_u16(&bitvec![1,1,0,0,1,0,0,1])
                .is_err()
        );
        Ok(())
    }

    #[test]
    fn symmetry_test() -> Result<()> {
        fn mask(n: u32, m: usize) -> u32 {
            n & 1u32.checked_shl(m as u32).unwrap_or(0).wrapping_sub(1)
        }

        for i in 1..=8 {
            let pattern = mask(0xc5c5c5c5, i) as u8;
            assert_eq!(i.encode_u8(pattern)?.len(), i);
            assert_eq!(
                i.decode_u8(&i.encode_u8(pattern)?)?,
                (pattern, i)
            );
        }

        for i in 1..=16 {
            let pattern = mask(0xc5c5c5c5, i) as u16;
            assert_eq!(i.encode_u16(pattern)?.len(), i);
            assert_eq!(
                i.decode_u16(&i.encode_u16(pattern)?)?,
                (pattern, i)
            );
        }

        for i in 1..=32 {
            let pattern = mask(0xc5c5c5c5, i) as u32;
            assert_eq!(i.encode_u32(pattern)?.len(), i);
            assert_eq!(
                i.decode_u32(&i.encode_u32(pattern)?)?,
                (pattern, i)
            );
        }

        for i in 1..=32 {
            let pattern = mask(0xc5c5c5c5, i) as u32;
            assert_eq!(i.encode_sym(pattern)?.len(), i);
            assert_eq!(
                i.decode_sym(&i.encode_sym(pattern)?)?,
                (pattern, i)
            );
        }

        assert_eq!(8.encode(b"hello world!")?.len(), 96);
        assert_eq!(
            8.decode::<u8>(&8.encode(b"hello world!")?)?,
            b"hello world!".to_vec()
        );

        Ok(())
    }
}
