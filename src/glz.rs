use std::collections::HashMap;

use crate::bits::*;
use crate::errors::*;

use error_chain::ensure;


// GLZ takes in 8-bit symbols and outputs 9ish-bit symbols. Further
// symbol-based compression can be applied on these 9-bit symbols.
//
// Bit 9 determines if the symbol is an immediate containing the original
// 8-bit symbol, or an LZ reference. LZ references are encoded as length+offset
// pairs, with the addition that the number of nibbles encoding the offset is
// also encoded in a offsetsize field.
//
// There are two parameters that control this encoding: L and M. L determines
// the number of bits that encode the length of references, and M determines
// the number of bits in each offset nibble (it may not be 4). The size of the
// offsetsize field is implicitly 8-L.
//
// Because of idiosyncrasies in our compression, a length of 0 or 1 never
// occurs, so length = length-2. Additionally, offsetsize of zero is fairly
// useless, so offsetsize = offsetsize-1. To make things more confusing, offset
// is not modified, but the nibbles are stored with an offset of -1, requiring
// offset = offset+1 to be able to represent zero. This wouldn't be needed if
// we didn't offset offsetsize, but encoding it this way allows an additional
// (2**M)**(2**L) offsets.
//
// immediate:
// [0|xxxxxxxx]
//        '-- 8-bit immediate
//
// reference:
// [1|zzz|yyyyy][xxx xxx xxx]
//     |    |         '-- (M*offsetsize)-bit offset - sum(2**(M*i)) + 1
//     |    '------------ L-bit length - 2
//     '----------------- (8-L)-bit offsetsize - 1
//
// The references themselves can get quite long, but we only emit them
// if they save space.

#[derive(Debug)]
pub struct GLZ<E: SymEncode = usize> {
    l: usize, // length of references
    m: usize, // width of offset chunks
    width: usize,
    encoder: E,
}

impl GLZ {
    pub const DEFAULT_L: usize          = 5;
    pub const DEFAULT_M: usize          = 3;
    pub const DEFAULT_WIDTH: usize      = 8;

    pub fn new(l: usize, m: usize) -> GLZ {
        GLZ::with_encoder(l, m, GLZ::DEFAULT_WIDTH, GLZ::DEFAULT_WIDTH+1)
    }

    pub fn with_width(l: usize, m: usize, width: usize) -> GLZ {
        GLZ::with_encoder(l, m, width, width+1)
    }
}

impl<E: SymEncode> GLZ<E> {
    pub fn with_encoder(
        l: usize,
        m: usize,
        width: usize,
        encoder: E,
    ) -> GLZ<E> {
        GLZ{
            l: l,
            m: m,
            width: width,
            encoder: encoder,
        }
    }

    pub fn l(&self) -> usize {
        self.l
    }

    pub fn m(&self) -> usize {
        self.m
    }

    pub fn width(&self) -> usize {
        self.width
    }

    fn encode_imm<U: Sym>(&self, c: U) -> Result<BitVec> {
        let imm: u32
            = (0u32 << self.width)
            | self.width.cast_u32(c)?;
        self.encoder.encode_u32(imm)
    }

    fn encode_ref(&self, off: usize, len: usize) -> Result<BitVec> {
        ensure!(len >= 0+2 && len <= 2usize.pow(self.l as u32)-1+2,
            "bad len {}", len);

        let mut offs: Vec<usize> = Vec::new();
        let mut noff = off + 1;
        while noff != 0 {
            noff -= 1;
            offs.push(noff & (2usize.pow(self.m as u32)-1));
            noff >>= self.m;
        }
        offs.reverse();

        let offsize = offs.len();
        ensure!(offsize >= 0+1 &&
            offsize <= 2usize.pow((self.width-self.l) as u32)-1+1,
            "bad offset {} (off = {})", offsize, off);

        let ref_: u32
            = (1u32 << self.width)
            | ((self.width-self.l).cast_u32(offsize as u32 - 1)? << self.l)
            | self.l.cast_u32(len as u32 - 2)?;

        Ok(self.encoder.encode_u32(ref_)?.iter()
            .chain(offs.iter()
                .map(|&off| self.m.encode_u32(off as u32))
                .collect::<Result<Vec<_>>>()?
                .into_iter().flatten())
            .collect())
    }

    fn encode1<'a, U: Sym>(
        &self,
        history: &mut HashMap<&'a [U], usize>,
        off: &mut usize,
        slice: &'a [U],
        mut prog: impl FnMut(usize),
    ) -> Result<BitVec> {
        let mut patterns: Vec<BitVec> = Vec::new();
        let mut j = slice.len();
        let mut lastmatch = j;
        let mut forceimm = false;
        while j > 0 {
            // find longest suffix in dictionary that matches criteria
            // this looks (and is) very expensive (O(n^2))
            let mut prefix: &[U] = &[slice[j-1]];
            let mut pref: Option<BitVec> = None;
            let lookahead = j
                .checked_sub(2usize.pow(self.l as u32))
                .unwrap_or(0);
            for i in (lookahead..j).rev() {
                if let Some(nref) = history
                    .get(&slice[i..j])
                    .and_then(|&poff|
                        self.encode_ref(*off-poff, slice[i..j].len()).ok()
                    )
                {
                    prefix = &slice[i..j];
                    pref = Some(nref);
                }
            }

            let consume: usize;
            let emit: usize;
            if forceimm || pref.as_ref().filter(|pref|
                pref.len() < (1+self.width)*prefix.len()
            ).is_none() {
                // not worth the overhead of the reference, emit immediate
                let imm = self.encode_imm(slice[j-1])
                    .chain_err(|| "could not encode GLZ sym")?;
                consume = 1;
                emit = imm.len();
                patterns.push(imm);
                forceimm = false;

                // add every prefix to dictionary since last match, note we
                // also update the substrings of our original match, which
                // should improve offset locality. This is worst case O(n^2)
                // if no repetition is ever found.
                let i = j-consume;
                for r in i+2..lastmatch+1 {
                    history.insert(&slice[i..r], *off+emit);
                }
            } else {
                // found a pattern, emit reference
                consume = prefix.len();
                emit = pref.as_ref().unwrap().len();
                patterns.push(pref.unwrap());

                // force an immediate to guarantee O(n) decompression (at
                // minimum one character per reference)
                lastmatch = j;
                forceimm = true;
            }

            prog(consume);
            j -= consume;
            *off += emit;
        }

        patterns.reverse();
        Ok(patterns.iter().flatten().collect())
    }

    fn decode1<U: Sym>(
        &self,
        bits: &BitSlice,
        off: usize,
        len: Option<usize>,
        prog: &mut impl FnMut(usize),
        depth: u32,
    ) -> Result<Vec<U>> {
        // check that we have bounded recursion
        ensure!(depth < 2, "exceeded max depth ({} < {})", depth, 2);

        let mut bytes: Vec<U> = Vec::new();
        let mut off = off;
        let mut cycles = 0;
        while match len {
            Some(len) => bytes.len() < len,
            None => off < bits.len(),
        } {
            // decode symbol
            let (sym, diff) = self.encoder.decode_u32_at(bits, off)
                .chain_err(|| format!("could not decode GLZ symbol"))?;

            if sym & (1 << self.width) == 0 {
                // found an immediate
                prog(1);
                bytes.push(self.width.cast(sym)?);
                off += diff;
            } else {
                // found an indirect reference
                let refoffsize = (((sym >> self.l)
                    & (2u32.pow((self.width-self.l) as u32)-1))
                    + 1) as usize;
                let reflen = ((sym
                    & (2u32.pow(self.l as u32)-1))
                    + 2) as usize;

                let refoffsize = refoffsize as usize;
                let mut refoff = 0;
                for i in 0..refoffsize {
                    refoff = (refoff << self.m) + 1
                        + self.m.decode_u32_at(bits, off+diff+self.m*i)?.0;
                }
                let refoff = (refoff - 1) as usize;
                off += diff + refoffsize*self.m;

                // tail recurse?
                if len.is_some() && reflen >= len.unwrap()-bytes.len() {
                    off += refoff;
                } else {
                    let ref_: Vec<U> = self.decode1(
                        bits,
                        off+refoff,
                        Some(reflen),
                        prog,
                        depth+1
                    )?;
                    bytes.extend(ref_);
                }
            }

            // check that runtime is linear
            cycles += 1;
            if len.is_some() {
                ensure!(cycles <= 2*len.unwrap() as u32,
                    "exceeded runtime limit ({} <= {})",
                        cycles, 2*len.unwrap());
            }
        }

        Ok(bytes)
    }

    pub fn map_syms<U: Sym, V: Sym, F: FnMut(V)>(
        &self,
        slice: &[U],
        f: F,
    ) -> Result<()> {
        self.map_syms_with_prog(slice, f, |_|())
    }

    pub fn map_syms_with_prog<U: Sym, V: Sym, F: FnMut(V)>(
        &self,
        slice: &[U],
        f: F,
        prog: impl FnMut(usize),
    ) -> Result<()> {
        self.map_syms_all_with_prog(&[slice], f, (|_|(), prog))
    }

    pub fn map_syms_all<U: Sym, V: Sym, F: FnMut(V)>(
        &self,
        slices: &[&[U]],
        f: F,
    ) -> Result<()> {
        self.map_syms_all_with_prog(slices, f, (|_|(), |_|()))
    }

    pub fn map_syms_all_with_prog<U: Sym, V: Sym, F: FnMut(V)>(
        &self,
        slices: &[&[U]],
        mut f: F,
        prog: (impl FnMut(usize), impl FnMut(usize)),
    ) -> Result<()> {
        let (bits, _) = self.encode_all_with_prog(slices, prog)?;
        let mut off = 0;
        while off < bits.len() {
            let (op, diff) = self.encoder.decode_u32_at(&bits, off)?;

            // pass to our callback
            f((1+self.width).cast(op)?);

            off += diff;
            if op & 1u32 << self.width != 0 {
                off += (((op >> self.l)
                    & (2u32.pow((self.width-self.l) as u32)-1))
                    + 1) as usize * self.m;
            }
        }

        Ok(())
    }
}

impl<E: SymEncode> Encode for GLZ<E> {
    fn encode_with_prog<U: Sym>(
        &self,
        bytes: &[U],
        prog: impl FnMut(usize),
    ) -> Result<BitVec> {
        self.encode1(&mut HashMap::new(), &mut 0, bytes, prog)
    }

    fn decode_with_prog<U: Sym>(
        &self,
        bits: &BitSlice,
        mut prog: impl FnMut(usize),
    ) -> Result<Vec<U>> {
        self.decode1(bits, 0, None, &mut prog, 0)
    }
}

impl<E: SymEncode> GranularEncode for GLZ<E> {
    fn encode_all_with_prog<U: Sym>(
        &self,
        slices: &[&[U]],
        mut prog: (impl FnMut(usize), impl FnMut(usize)),
    ) -> Result<(BitVec, Vec<(usize, usize)>)> {
        let mut history: HashMap<&[U], usize> = HashMap::new();
        let mut off = 0; // compressed offset

        let bits: Vec<BitVec> = slices
            .into_iter().rev()
            .map(|slice| {
                let bits = self.encode1(
                    &mut history, &mut off, slice, &mut prog.1);
                prog.0(1);
                bits
            }).collect::<Result<Vec<_>>>()?
            .into_iter().rev()
            .collect();

        let mut off = 0; // uncompressed offset
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
        self.decode1(bits, off, Some(len), &mut prog, 0)
    }
}


#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn encode_imm_test() -> Result<()> {
        let glz = GLZ::new(5, 3);
        assert_eq!(
            glz.encode_imm(b'a')?,
            bitvec![
                0,
                0, 1, 1, 0, 0, 0, 0, 1
            ]
        );

        Ok(())
    }

    #[test]
    fn encode_ref_test() -> Result<()> {
        let glz = GLZ::new(5, 3);
        assert_eq!(
            glz.encode_ref(21, 12)?,
            bitvec![
                1,
                0, 0, 1,
                0, 1, 0, 1, 0,
                0, 0, 1,
                1, 0, 1
            ]
        );
        let glz = GLZ::new(7, 7);
        assert_eq!(
            glz.encode_ref(21, 12)?,
            bitvec![
                1,
                0,
                0, 0, 0, 1, 0, 1, 0,
                0, 0, 1, 0, 1, 0, 1
            ]
        );
        let glz = GLZ::new(8, 8);
        assert_eq!(
            glz.encode_ref(21, 12)?,
            bitvec![
                1,
                0, 0, 0, 0, 1, 0, 1, 0,
                0, 0, 0, 1, 0, 1, 0, 1
            ]
        );
        let glz = GLZ::new(4, 1);
        assert_eq!(
            glz.encode_ref(21, 12)?,
            bitvec![
                1,
                0, 0, 1, 1,
                1, 0, 1, 0,
                0,
                1,
                1,
                1
            ]
        );

        Ok(())
    }

    #[test]
    fn symmetry_test() -> Result<()> {
        let glz = GLZ::new(5, 3);
        assert_eq!(glz.encode(b"hello world!")?.len(), 108);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(b"hello world!")?)?,
            b"hello world!".to_vec()
        );

        let glz = GLZ::new(5, 3);
        let phrase = b"hello world hello hello world!";
        assert_eq!(glz.encode(phrase)?.len(), 144);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let glz = GLZ::new(5, 3);
        let phrase = b"hhhhh wwwww hhhhh hhhhh wwwww!";
        assert_eq!(glz.encode(phrase)?.len(), 207);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let glz = GLZ::new(5, 3);
        let phrase = b"hhhhh hhhhh hhhhh hhhhh hhhhh!";
        assert_eq!(glz.encode(phrase)?.len(), 192);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let glz = GLZ::new(5, 3);
        let phrase = b"hhhhhhhhhhhhhhhhhhhhhhhhhhhhh!";
        assert_eq!(glz.encode(phrase)?.len(), 144);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let glz = GLZ::new(5, 3);
        let phrase = b"hhhhhhhhhhhhhhhhhhhhhhhhhhhhhh";
        assert_eq!(glz.encode(phrase)?.len(), 135);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        Ok(())
    }
}
