//!
//! GLZ, granular compression
//!
//! Copyright (c) 2020, Arm Limited. All rights reserved.
//! SPDX-License-Identifier: BSD-3-Clause
//!

use std::collections::HashMap;

use crate::bits::*;
use crate::errors::*;
use crate::rice::GolombRice;
use crate::hist::Hist;
use crate::hist::BijectEncoder;
use std::cmp::Reverse;

use error_chain::ensure;


// GLZ, or granular Lempel-Ziv, is an approach to granular compression
// built through careful application of Lempel-Ziv in order to maintain
// O(1) RAM consumption and O(n) decompression cost. GLZ combines this with
// Golomb-Rice codes to create a compact, granular compression where slices
// are _very_ cheap to decompress.
//
// From a high-level, GLZ takes in 8-bit symbols and outputs 9ish-bit symbols
// representing either an immediate literal or an indirect LZ reference. LZ
// references are encoded as length+offset pairs, with the offset encoded as
// a small variable length field following the reference symbol containing the
// reference length.
//
// There are three parameters that control this encoding: K, L and M.
// L determines the number of bits that encode the length of references,
// M determines the number of bits that encode the nibbles in an argument,
// and K provides the Golomb-Rice constant that determines how tight our total
// distribution of symbols is.
//
// Because of idiosyncrasies in our compression, a length of 0 or 1 never
// occurs, so we offset length = length-2.
//
// immediate:
// [0xxxxxxxx]
//       ^-- 8-bit immediate
//
// reference:
// [1000yyyyy|1xxx|1xxx|0xxx]
//        ^   \-----------/
//        |          '-- M*i-bit offset - sum(2^(M*i)) + 1
//        '------------- L-bit length - 2
//
// This gives us a total number of unique symbols = 2^8 + 2^L. These symbols
// can be redistributed by a 9-bit probability table to maximize the
// compactness of the Golomb-Rice codes. Fortunately, Golomb-Rice codes don't
// necessarily need to be a power-of-two, so our table wastes no encoding space
// as long as for all X in {8, L}, X >= K. Additionally, we can garuntee 8-bit
// alignment as long as for all X in {8, L}, 2^X > 8.
//
// The references themselves can get quite long, but we only emit them
// if they save space.

#[derive(Debug, Clone)]
pub struct GLZ {
    l: usize, // size of length field in references
    m: usize, // size of offset units
    rice: BijectEncoder<GolombRice, Hist>,
}

#[derive(Debug, Copy, Clone, PartialEq)]
enum GLZSym<U: Sym> {
    Imm(U),
    Ref{off: usize, size: usize},
}

impl GLZ {
    pub const DEFAULT_K: usize  = GLZ::WIDTH+1;
    pub const DEFAULT_L: usize  = 5;
    pub const DEFAULT_M: usize  = 4;
    pub const WIDTH: usize      = 8;

    pub fn new() -> Self {
        Self::with_config(Self::DEFAULT_K, Self::DEFAULT_L, Self::DEFAULT_M)
    }

    pub fn with_config(k: usize, l: usize, m: usize) -> Self {
        Self{
            l: l,
            m: m,
            rice: BijectEncoder::new(
                GolombRice::new(k),
                Hist::new(),
            ),
        }
    }

    pub fn with_table<U: Sym>(
        k: usize,
        l: usize,
        m: usize,
        decode_table: &[U],
    ) -> Self {
        Self{
            l: l,
            m: m,
            rice: BijectEncoder::new(
                GolombRice::new(k),
                Hist::with_table(decode_table),
            ),
        }
    }

    pub fn from_hist(
        k: Option<usize>,
        l: usize,
        m: usize,
        hist: &Hist,
    ) -> Self {
        // use hist as bijecter to map probabilities to best rice code
        let mut hist = hist.clone();
        hist.sort();
        hist.compact();

        let rice = if let Some(k) = k {
            GolombRice::new(k)
        } else {
            GolombRice::from_hist(&hist)
        };

        Self{
            l: l,
            m: m,
            rice: BijectEncoder::new(
                rice,
                hist,
            ),
        }
    }

    pub fn from_seed<I: IntoIterator<Item=U>, U: Sym>(
        k: Option<usize>,
        l: usize,
        m: usize,
        seed: I,
    ) -> Self {
        let glz = Self::with_config(k.unwrap_or(Self::DEFAULT_K), l, m);
        let mut hist = Hist::new();
        let bits = glz.encode(&seed.into_iter().collect::<Vec<_>>()).unwrap();
        glz.traverse_syms(&bits, |op: u32| {
            hist.increment(op);
        }).unwrap();

        Self::from_hist(k, l, m, &hist)
    }

    pub fn k(&self) -> usize {
        self.rice.encoder().k()
    }

    pub fn l(&self) -> usize {
        self.l
    }

    pub fn m(&self) -> usize {
        self.m
    }

    pub fn encode_table<U: Sym>(&self) -> Result<Vec<U>> {
        self.rice.bijecter().encode_table()
    }

    pub fn decode_table<U: Sym>(&self) -> Result<Vec<U>> {
        self.rice.bijecter().decode_table()
    }

    fn encode_sym_raw<U: Sym>(&self, sym: GLZSym<U>) -> Result<BitVec> {
        let sym = match sym {
            GLZSym::Imm(x) => {
                self.rice.encode_u32(u32::cast(x)?)?
            }
            GLZSym::Ref{off, size} => {
                //ensure!(off >= 0, "bad offset {}", off);
                ensure!(size >= 2 && size <= 2usize.pow(self.l as u32)-1+2,
                    "bad size {}", size);
                let off = off as u32;
                let nsize = (size - 2) as u32
                    + 2u32.pow(Self::WIDTH as u32);

                let mut offs: Vec<u32> = Vec::new();
                let mut noff = off + 1;
                while noff != 0 {
                    noff -= 1;
                    offs.push(noff & (2u32.pow(self.m as u32)-1));
                    noff >>= self.m;
                }
                offs.reverse();

                self.rice.encode_u32(nsize)?.into_iter()
                    .chain(offs.iter()
                        .enumerate()
                        .map(|(i, &nibble)| (self.m+1).encode_u32(
                            nibble | ((!(i == offs.len()-1) as u32) << self.m)
                        ))
                        .collect::<Result<Vec<_>>>()?
                        .into_iter().flatten())
                    .collect()
            }
        };

        Ok(sym)
    }

    fn encode_sym<U: Sym>(&self, sym: GLZSym<U>) -> Result<BitVec> {
        self.encode_sym_raw(sym)
            .chain_err(|| format!("could not encode GLZ symbol {:?}", sym))
    }

    fn decode_sym_raw<U: Sym>(
        &self,
        bits: &BitSlice
    ) -> Result<(GLZSym<U>, usize)> {
        let mut off = 0;
        let (sym, diff) = self.rice.decode_u32_at(bits, off)?;
        off += diff;

        let sym = if sym < 2u32.pow(Self::WIDTH as u32) {
            // found an immediate
            GLZSym::Imm(U::cast(sym)?)
        } else {
            // found indirect reference
            let mut arg = 0;
            loop {
                let (sym, diff) = (self.m+1).decode_u32_at(bits, off)?;
                off += diff;
                arg = (arg << self.m) + 1 + (sym & (2u32.pow(self.m as u32)-1));
                if sym < 2u32.pow(self.m as u32) {
                    break;
                }
            }

            GLZSym::Ref{
                off: arg as usize - 1,
                size: sym as usize - 2usize.pow(Self::WIDTH as u32) + 2,
            }
        };

        Ok((sym, off))
    }

    fn decode_sym<U: Sym>(
        &self,
        bits: &BitSlice
    ) -> Result<(GLZSym<U>, usize)> {
        self.decode_sym_raw(bits)
            .chain_err(|| "could not decode GLZ symbol")
    }

    fn decode_sym_at<U: Sym>(
        &self,
        bits: &BitSlice,
        off: usize
    ) -> Result<(GLZSym<U>, usize)> {
        self.decode_sym(&bits[off..])
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
            let mut refconsume = 0;
            let mut ref_: Option<BitVec> = None;
            let lookahead = j
                .checked_sub(2usize.pow(self.l as u32))
                .unwrap_or(0);
            for i in (lookahead..j).rev() {
                if let Some(nref) = history
                    .get(&slice[i..j])
                    .and_then(|&poff|
                        self.encode_sym::<U>(GLZSym::Ref{
                            off: *off-poff,
                            size: slice[i..j].len(),
                        }).ok()
                    )
                {
                    refconsume = j-i;
                    ref_ = Some(nref);
                }
            }
            let refratio = ref_.as_ref()
                .map(|ref_| refconsume as f64 / ref_.len() as f64)
                .unwrap_or(0.0);

            let immconsume = 1;
            let imm = self.encode_sym(GLZSym::Imm(slice[j-1]))?;
            let immratio = immconsume as f64 / imm.len() as f64;

            let consume: usize;
            let emit: usize;
            if forceimm || immratio >= refratio {
                // not worth the overhead of the reference, emit immediate(s)
                consume = immconsume;
                emit = imm.len();
                patterns.push(imm);
                forceimm = false;

                // add every prefix to dictionary since last match, note we
                // also update the substrings of our original match, which
                // should improve offset locality. This is worst case O(n^2)
                // if no repetition is ever found.
                let i = j-consume;
                for r in (i+2..lastmatch+1).take(2usize.pow(self.l as u32)) {
                    history.insert(&slice[i..r], *off+emit);
                }
            } else {
                // found a pattern, emit reference
                consume = refconsume;
                emit = ref_.as_ref().unwrap().len();
                patterns.push(ref_.unwrap());

                // force an immediate to guarantee O(n) decompression (at
                // minimum one character per reference)
                lastmatch = j;
                forceimm = true;
            }

            prog(consume);
            j -= consume;
            *off += emit;
        }

        Ok(patterns.into_iter().rev().flatten().collect())
    }

    fn decode1<U: Sym>(
        &self,
        bits: &BitSlice,
        off: usize,
        size: Option<usize>,
        prog: &mut impl FnMut(usize),
        depth: u32,
    ) -> Result<Vec<U>> {
        // check that we have bounded recursion
        ensure!(depth < 2, "exceeded max depth ({} < {})", depth, 2);

        let mut bytes: Vec<U> = Vec::new();
        let mut off = off;
        let mut cycles = 0;
        while match size {
            Some(size) => bytes.len() < size,
            None => off < bits.len(),
        } {
            // decode symbol
            match self.decode_sym_at::<U>(bits, off)? {
                (GLZSym::Imm(x), diff) => {
                    bytes.push(x);
                    off += diff;
                    prog(1);
                }
                (GLZSym::Ref{off: refoff, size: refsize}, diff) => {
                    off += diff;
                    if size.is_some() && refsize >= size.unwrap()-bytes.len() {
                        off += refoff;
                    } else {
                        let ref_: Vec<U> = self.decode1(
                            bits,
                            off + refoff,
                            Some(refsize),
                            prog,
                            depth + 1,
                        )?;
                        bytes.extend(ref_);
                    }
                }
            }

            // check that runtime is linear
            cycles += 1;
            if size.is_some() {
                ensure!(cycles <= 2*size.unwrap() as u32,
                    "exceeded runtime limit ({} <= {})",
                        cycles, 2*size.unwrap());
            }
        }

        Ok(bytes)
    }

    // traversal functions, intended for building up histograms
    pub fn traverse_syms<U: Sym, F: FnMut(U)>(
        &self,
        bits: &BitSlice,
        f: F
    ) -> Result<()> {
        self.traverse_syms_with_prog(bits, f, |_|())
    }

    pub fn traverse_syms_with_prog<U: Sym, F: FnMut(U)>(
        &self,
        bits: &BitSlice,
        mut f: F,
        mut prog: impl FnMut(usize)
    ) -> Result<()> {
        let mut off = 0;
        while off < bits.len() {
            // decode symbol
            let (sym, diff) = self.rice.decode_sym_at(bits, off)?;
            off += diff;
            f(sym);
            prog(1);

            // skip arg
            if u32::cast(sym)? >= 2u32.pow(Self::WIDTH as u32) {
                loop {
                    let (sym, diff) = (self.m+1).decode_u32_at(bits, off)?;
                    off += diff;
                    if sym < 2u32.pow(self.m as u32) {
                        break;
                    }
                }
            }
        }

        Ok(())
    }
}

impl Encode for GLZ {
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

impl GranularEncode for GLZ {
    fn encode_all_with_prog<U: Sym, T>(
        &self,
        slices: &[&[U]],
        mut prog: (impl IntoIterator<Item=T>, impl FnMut(T), impl FnMut(usize)),
    ) -> Result<(BitVec, Vec<(usize, usize)>)> {
        let mut history: HashMap<&[U], usize> = HashMap::new();
        let mut off = 0; // compressed offset

        // sort so that smaller slices have smaller offset values
        let mut sorted_slices: Vec<_> = slices.iter()
            .zip(prog.0)
            .collect();
        sorted_slices.sort_by_key(|(slice, _)| Reverse(slice.len()));

        let mut offs: HashMap<&[U], usize> = HashMap::new();
        let mut blobs: Vec<BitVec> = Vec::new();
        for (slice, tag) in sorted_slices {
            prog.1(tag);
            if offs.contains_key(slice) {
                // found duplicate in blob? deduplicate
            } else if let Some(off) = history.get(slice).copied() {
                // found slice inside a pattern
                offs.insert(slice, off);
            } else {
                // compress our slice
                blobs.push(self.encode1(
                    &mut history,
                    &mut off,
                    slice,
                    &mut prog.2)?);
                offs.insert(slice, off);
            }
        }

        let total: usize = blobs.iter().map(|b| b.len()).sum();
        Ok((
            // build blob
            blobs.into_iter()
                .rev()
                .flatten()
                .collect(),
            // collect offsets+size pairs in the original order
            slices.into_iter()
                .map(|slice| (
                    total - offs.get(slice).copied().unwrap(),
                    slice.len(),
                ))
                .collect(),
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
        let glz = GLZ::with_config(9, 5, 3);
        assert_eq!(
            glz.encode_sym::<u8>(GLZSym::Imm(b'a'))?,
            bitvec![
                0,0,0,1,1,0,0,0,0,1
            ]
        );

        Ok(())
    }

    #[test]
    fn encode_ref_test() -> Result<()> {
        let glz = GLZ::with_config(9, 5, 3);
        assert_eq!(
            glz.encode_sym::<u8>(GLZSym::Ref{off:21, size:12})?,
            bitvec![
                0,1,0,0,0,0,1,0,1,0,
                1,0,0,1,
                0,1,0,1,
            ]
        );
        let glz = GLZ::with_config(9, 7, 7);
        assert_eq!(
            glz.encode_sym::<u8>(GLZSym::Ref{off:21, size:12})?,
            bitvec![
                0,1,0,0,0,0,1,0,1,0,
                0,0,0,1,0,1,0,1,
            ]
        );
        let glz = GLZ::with_config(9, 8, 8);
        assert_eq!(
            glz.encode_sym::<u8>(GLZSym::Ref{off:21, size:12})?,
            bitvec![
                0,1,0,0,0,0,1,0,1,0,
                0,0,0,0,1,0,1,0,1,
            ]
        );
        let glz = GLZ::with_config(9, 4, 1);
        assert_eq!(
            glz.encode_sym::<u8>(GLZSym::Ref{off:21, size:12})?,
            bitvec![
                0,1,0,0,0,0,1,0,1,0,
                1,0,
                1,1,
                1,1,
                0,1,
            ]
        );

        Ok(())
    }

    #[test]
    fn sym_symmetry_test() -> Result<()> {
        let glz = GLZ::with_config(8, 5, 3);
        let sym = GLZSym::Imm(b'a');
        assert_eq!(
            glz.decode_sym::<u8>(&glz.encode_sym::<u8>(sym)?)?,
            (sym, 9)
        );
        let sym = GLZSym::Ref{off: 21, size: 12};
        assert_eq!(
            glz.decode_sym::<u8>(&glz.encode_sym::<u8>(sym)?)?,
            (sym, 18)
        );
        let sym = GLZSym::Ref{off: 0, size: 2};
        assert_eq!(
            glz.decode_sym::<u8>(&glz.encode_sym::<u8>(sym)?)?,
            (sym, 14)
        );
        let sym = GLZSym::Ref{off: 123456, size: 31};
        assert_eq!(
            glz.decode_sym::<u8>(&glz.encode_sym::<u8>(sym)?)?,
            (sym, 34)
        );

        Ok(())
    }

    #[test]
    fn symmetry_test() -> Result<()> {
        let glz = GLZ::with_config(8, 5, 3);
        assert_eq!(glz.encode(b"hello world!")?.len(), 108);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(b"hello world!")?)?,
            b"hello world!".to_vec()
        );

        let phrase = b"hello world hello hello world!";
        assert_eq!(glz.encode(phrase)?.len(), 149);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let phrase = b"hhhhh wwwww hhhhh hhhhh wwwww!";
        assert_eq!(glz.encode(phrase)?.len(), 226);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let phrase = b"hhhhh hhhhh hhhhh hhhhh hhhhh!";
        assert_eq!(glz.encode(phrase)?.len(), 168);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let phrase = b"hhhhhhhhhhhhhhhhhhhhhhhhhhhhh!";
        assert_eq!(glz.encode(phrase)?.len(), 156);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let phrase = b"hhhhhhhhhhhhhhhhhhhhhhhhhhhhhh";
        assert_eq!(glz.encode(phrase)?.len(), 147);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        Ok(())
    }

    #[test]
    fn seeded_symmetry_test() -> Result<()> {
        let phrase = b"hello world!";
        let glz = GLZ::from_seed(None, 5, 3, phrase.iter().copied());
        assert_eq!(glz.k(), 1);
        assert_eq!(glz.encode(phrase)?.len(), 40);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let phrase = b"hello world hello hello world!";
        let glz = GLZ::from_seed(None, 5, 3, phrase.iter().copied());
        assert_eq!(glz.k(), 2);
        assert_eq!(glz.encode(phrase)?.len(), 67);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let phrase = b"hhhhh wwwww hhhhh hhhhh wwwww!";
        let glz = GLZ::from_seed(None, 5, 3, phrase.iter().copied());
        assert_eq!(glz.k(), 1);
        assert_eq!(glz.encode(phrase)?.len(), 66);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let phrase = b"hhhhh hhhhh hhhhh hhhhh hhhhh!";
        let glz = GLZ::from_seed(None, 5, 3, phrase.iter().copied());
        assert_eq!(glz.k(), 0);
        assert_eq!(glz.encode(phrase)?.len(), 49);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let phrase = b"hhhhhhhhhhhhhhhhhhhhhhhhhhhhh!";
        let glz = GLZ::from_seed(None, 5, 3, phrase.iter().copied());
        assert_eq!(glz.k(), 0);
        assert_eq!(glz.encode(phrase)?.len(), 32);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let phrase = b"hhhhhhhhhhhhhhhhhhhhhhhhhhhhhh";
        let glz = GLZ::from_seed(None, 5, 3, phrase.iter().copied());
        assert_eq!(glz.k(), 0);
        assert_eq!(glz.encode(phrase)?.len(), 30);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        Ok(())
    }
}
