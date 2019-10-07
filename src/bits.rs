use std::convert::TryFrom;
use std::hash;

pub use bitvec::prelude::*;


// Symbols that can be encoded (u8, u16, u32)
// Note these can all be expanded to u32
#[allow(dead_code)]
pub trait Sym: TryFrom<u32> + Into<u32> + Copy + Eq + hash::Hash {
    fn encode_sym(width: usize, n: Self) -> Result<BitVec, String>;
    fn decode_sym(width: usize, bits: &BitSlice) -> Result<Self, String>;
}

#[allow(dead_code)]
impl Sym for u8 {
    fn encode_sym(width: usize, n: u8) -> Result<BitVec, String> {
        Ok(BitVec::from_bitslice(&n.as_bitslice::<BigEndian>()[8-width..]))
    }

    fn decode_sym(width: usize, bits: &BitSlice) -> Result<u8, String> {
        u32::decode_sym(width, bits).map(|n| n as u8)
    }
}

#[allow(dead_code)]
impl Sym for u16 {
    fn encode_sym(width: usize, n: u16) -> Result<BitVec, String> {
        u32::encode_sym(width, u32::from(n))
    }

    fn decode_sym(width: usize, bits: &BitSlice) -> Result<u16, String> {
        u32::decode_sym(width, bits).map(|n| n as u16)
    }
}

#[allow(dead_code)]
impl Sym for u32 {
    fn encode_sym(width: usize, n: u32) -> Result<BitVec, String> {
        Ok(n.as_bitslice::<BigEndian>()[32-width..].iter().collect())
    }

    fn decode_sym(width: usize, bits: &BitSlice) -> Result<u32, String> {
        if bits.len() < width {
            return Err(format!("found truncated u{}", width));
        }

        Ok(bits[..width].iter().enumerate().fold(0, |s, (i, v)|
            s | (u32::from(v) << ((width - i - 1) as u32))
        ))
    }
}

macro_rules! mkrule {
    ($name:ident { $target:ident($u:ty$(, $x:ident: $xt:ty)*) }) => {
        fn $name(&self, n: $u$(, $x: $xt)*) -> Result<BitVec, String> {
            self.$target(n$(, $x)*)
        }
    };

    ($name:ident { $target:ident!($u:ty$(, $x:ident: $xt:ty)*) }) => {
        fn $name(&self, n: $u$(, $x: $xt)*) -> Result<BitVec, String> {
            self.$target(n$(, $x)*)
        }
    };

    ($name:ident { $target:ident($($x:ident: $xt:ty),*) -> $u:ty }) => {
        fn $name(&self, bits: &BitSlice$(, $x: $xt)*) -> Result<$u, String> {
            self.$target(bits$(, $x)*)
        }
    };
}

// Generalized encoder, operates on streams of symbols
pub trait Encode {
    fn encode<U: Sym>(&self, bytes: &[U]) -> Result<BitVec, String>;
    fn decode<U: Sym>(&self, bits: &BitSlice) -> Result<Vec<U>, String>;

    mkrule!(encode_u8s  { encode!(&[u8])  });
    mkrule!(encode_u16s { encode!(&[u16]) });
    mkrule!(encode_u32s { encode!(&[u32]) });
    mkrule!(decode_u8s  { decode() -> Vec<u8>  });
    mkrule!(decode_u16s { decode() -> Vec<u16> });
    mkrule!(decode_u32s { decode() -> Vec<u32> });
}

// Symbol encoder, operates on variable sized symbols
pub trait SymEncode {
    fn encode_sym<U: Sym>(&self, n: U)
        -> Result<BitVec, String>;
    fn decode_sym<U: Sym>(&self, bits: &BitSlice)
        -> Result<(U, usize), String>;

    fn cast<U: Sym, V: Sym>(&self, n: U) -> Result<V, String> {
        Ok(self.decode_sym(&self.encode_sym(n)?)?.0)
    }

    fn decode_sym_at<U: Sym>(
        &self,
        bits: &BitSlice,
        off: usize
    ) -> Result<(U, usize), String> {
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
    fn encode<U: Sym>(&self, bytes: &[U]) -> Result<BitVec, String> {
        Ok(bytes.iter()
            .map(|&n| self.encode_sym(n))
            .collect::<Result<Vec<_>, _>>()?
            .into_iter().flatten()
            .collect())
    }

    fn decode<U: Sym>(&self, bits: &BitSlice) -> Result<Vec<U>, String> {
        let mut words: Vec<U> = Vec::new();
        let mut off = 0;
        while off < bits.len() {
            let (n, diff) = self.decode_sym_at(bits, off)?;
            words.push(n);
            off += diff;
        }
        Ok(words)
    }
}

pub trait MultiEncode {
    fn encode_all<U: Sym>(
        &self,
        slices: &[&[U]]
    ) -> Result<(BitVec, Vec<(usize, usize)>), String>;

    fn decode_all<U: Sym>(
        &self,
        bits: &BitSlice,
        offs: &[(usize, usize)]
    ) -> Result<Vec<Vec<U>>, String> {
        offs.iter().map(|(off, len)|
            self.decode_at(bits, *off, *len)
        ).collect()
    }

    fn decode_at<U: Sym>(
        &self,
        bits: &BitSlice,
        off: usize,
        len: usize
    ) -> Result<Vec<U>, String>;

    mkrule!(decode_u8s_at  { decode_at(off: usize, len: usize) -> Vec<u8>  });
    mkrule!(decode_u16s_at { decode_at(off: usize, len: usize) -> Vec<u16> });
    mkrule!(decode_u32s_at { decode_at(off: usize, len: usize) -> Vec<u32> });
}

impl<T: SymEncode> MultiEncode for T {
    fn encode_all<U: Sym>(
        &self,
        slices: &[&[U]]
    ) -> Result<(BitVec, Vec<(usize, usize)>), String> {
        let bits = slices.iter()
            .map(|slice| self.encode(slice))
            .collect::<Result<Vec<_>, _>>()?;

        let mut off = 0;
        Ok((
            bits.iter().flatten().collect(),
            bits.iter().zip(slices).map(|(bits, slice)| {
                off += bits.len();
                (off-bits.len(), slice.len())
            }).collect()
        ))
    }

    fn decode_at<U: Sym>(
        &self,
        bits: &BitSlice,
        off: usize,
        len: usize)
    -> Result<Vec<U>, String> {
        let mut words = Vec::new();
        let mut off = off;
        while words.len() < len {
            let (n, diff) = self.decode_sym_at(bits, off)?;
            words.push(n);
            off += diff;
        }
        Ok(words)
    }
}

// A usize value can be a symbol encoder (fixed width integers)
impl SymEncode for usize {
    fn encode_sym<U: Sym>(&self,
        n: U
    ) -> Result<BitVec, String> {
        U::encode_sym(*self, n)
    }

    fn decode_sym<U: Sym>(&self,
        bits: &BitSlice
    ) -> Result<(U, usize), String> {
        U::decode_sym(*self, bits).map(|v| (v, *self))
    }

    fn cast<U: Sym, V: Sym>(&self, n: U) -> Result<V, String> {
        let n: u32 = n.into();
        if *self >= 32 || n < 2u32.pow(*self as u32) {
            Ok(V::try_from(n).ok().unwrap())
        } else {
            Err(format!("exceeded size of u{} with {}", *self, n))
        }
    }
}


#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn symmetry_test() {
        fn mask(n: u32, m: usize) -> u32 {
            n & 1u32.checked_shl(m as u32).unwrap_or(0).wrapping_sub(1)
        }

        for i in 1..=8 {
            assert_eq!(i.encode_u8(0xc5u8).unwrap().len(), i);
            assert_eq!(
                i.decode_u8(&i.encode_u8(0xc5u8).unwrap()),
                Ok((mask(0xc5, i) as u8, i))
            );
        }

        for i in 1..=16 {
            assert_eq!(i.encode_u16(0xc5c5u16).unwrap().len(), i);
            assert_eq!(
                i.decode_u16(&i.encode_u16(0xc5c5u16).unwrap()),
                Ok((mask(0xc5c5, i) as u16, i))
            );
        }

        for i in 1..=32 {
            assert_eq!(i.encode_u32(0xc5c5c5c5u32).unwrap().len(), i);
            assert_eq!(
                i.decode_u32(&i.encode_u32(0xc5c5c5c5u32).unwrap()),
                Ok((mask(0xc5c5c5c5, i) as u32, i))
            );
        }

        for i in 1..=32 {
            assert_eq!(i.encode_sym(0xc5c5c5c5u32).unwrap().len(), i);
            assert_eq!(
                i.decode_sym(&i.encode_sym(0xc5c5c5c5u32).unwrap()),
                Ok((mask(0xc5c5c5c5, i) as u32, i))
            );
        }

        assert_eq!(8.encode(b"hello world!").unwrap().len(), 96);
        assert_eq!(
            8.decode(&8.encode(b"hello world!").unwrap()),
            Ok(b"hello world!".to_vec())
        );
    }
}
