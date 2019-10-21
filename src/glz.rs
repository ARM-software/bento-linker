use std::collections::HashMap;
use std::iter;

use crate::bits::*;
use crate::errors::*;
use crate::rice::GolombRice;
use crate::rice::GolombRice_;
use crate::hist::Hist;
use crate::hist::BijectEncoder;

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
// TODO ^^^ update this ^^^

#[derive(Debug, Clone)]
pub struct GLZ_ {
    l: usize, // size of length field in references
    m: usize, // size of offset units
    rice: BijectEncoder<GolombRice_, Hist>,
}

#[derive(Debug, Copy, Clone, PartialEq)]
enum GLZSym<U: Sym> {
    Imm{count: usize, imm: U},
    Ref{off: usize, size: usize},
}

impl GLZ_ {
    pub const DEFAULT_K: usize  = GLZ_::WIDTH+1-1;
    pub const DEFAULT_L: usize  = 5;
    pub const DEFAULT_M: usize  = 3;
    pub const WIDTH: usize      = 8;

    pub fn new() -> Self {
        Self::with_config(Self::DEFAULT_K, Self::DEFAULT_L, Self::DEFAULT_M)
    }

    pub fn with_config(k: usize, l: usize, m: usize) -> Self {
        Self{
            l: l,
            m: m,
            rice: BijectEncoder::new(
                GolombRice_::new(k),
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
                GolombRice_::new(k),
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
        hist.sort_bounded(
            2usize.pow(Self::WIDTH as u32) +
            2usize.pow(l as u32));

        let rice = if let Some(k) = k {
            GolombRice_::new(k)
        } else {
            GolombRice_::from_hist(&hist)
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
        match sym {
            GLZSym::Imm{count, imm: x} => {
                let mut counts: Vec<usize> = Vec::new();
                let mut ncount = count + 1 - 2;
                while ncount != 0 {
                    ncount -= 1;
                    counts.push(ncount & (2usize.pow(self.m as u32)-1));
                    ncount >>= self.m;
                }
                counts.reverse();

                let countsize = counts.len();

                let imm: u32
                    = (0u32 << Self::WIDTH)
                    | u32::cast(x)?;

                Ok(self.rice.encode_u32(((countsize as u32 - 0) * ((1 << Self::WIDTH as u32) + (1 << self.l as u32))) + imm)?.iter()
                    .chain(counts.iter()
                        .map(|&count| self.m.encode_u32(count as u32))
                        .collect::<Result<Vec<_>>>()?
                        .into_iter().flatten())
                    .collect())
//                Ok(self.rice.encode_u32(((countsize as u32 - 0) << (1+Self::WIDTH as u32)) + imm)?.iter()
//                    .chain(counts.iter()
//                        .map(|&count| self.m.encode_u32(count as u32))
//                        .collect::<Result<Vec<_>>>()?
//                        .into_iter().flatten())
//                    .collect())
            }
            GLZSym::Ref{off, size} => {
                ensure!(size >= 0+2 && size <= 2usize.pow(self.l as u32)-1+2,
                    "bad size {}", size);

                let mut offs: Vec<usize> = Vec::new();
                let mut noff = off + 1;
                while noff != 0 {
                    noff -= 1;
                    offs.push(noff & (2usize.pow(self.m as u32)-1));
                    noff >>= self.m;
                }
                offs.reverse();

                let offsize = offs.len();
//                ensure!(offsize >= 0+1 &&
//                    offsize <= 2usize.pow((Self::WIDTH-self.l) as u32)-1+1,
//                    "bad offset {} (off = {})", offsize, off);

                let ref_: u32
                    = (1u32 << Self::WIDTH)
//                    | ((Self::WIDTH-self.l).cast_u32(offsize as u32 - 1)?
//                        << self.l)
                    | u32::cast(size as u32 - 2)?;

                Ok(self.rice.encode_u32(((offsize as u32 - 0) * ((1 << Self::WIDTH as u32) + (1 << self.l as u32))) + ref_)?.iter()
                    .chain(offs.iter()
                        .map(|&off| self.m.encode_u32(off as u32))
                        .collect::<Result<Vec<_>>>()?
                        .into_iter().flatten())
                    .collect())
//                Ok(self.rice.encode_u32(((offsize as u32 - 0) << (1+Self::WIDTH as u32)) + ref_)?.iter()
//                    .chain(offs.iter()
//                        .map(|&off| self.m.encode_u32(off as u32))
//                        .collect::<Result<Vec<_>>>()?
//                        .into_iter().flatten())
//                    .collect())
            }
        }
    }

    fn encode_sym<U: Sym>(&self, sym: GLZSym<U>) -> Result<BitVec> {
        self.encode_sym_raw(sym)
            .chain_err(|| format!("could not encode GLZ symbol {:?}", sym))
    }

    fn decode_sym_raw<U: Sym>(
        &self,
        bits: &BitSlice
    ) -> Result<(GLZSym<U>, usize)> {
        // decode symbol
        let (sym, diff) = self.rice.decode_u32(bits)
            .chain_err(|| format!("could not decode GLZ symbol"))?;

        //if sym & (1 << Self::WIDTH) == 0 {
        //if sym < (1 << Self::WIDTH) {
        if (sym % ((1 << Self::WIDTH as u32) + (1 << self.l as u32))) < (1 << Self::WIDTH) {
            // found an immediate

            //let countsize = (sym >> (1 + Self::WIDTH)) + 0;
            let bound = (1 << Self::WIDTH as u32) + (1 << self.l as u32);
            let countsize = (sym / bound) + 0;
            let imm = sym % bound;

            let countsize = countsize as usize;
            let mut count = 0;
            for i in 0..countsize {
                count = (count << self.m) + 1
                    + self.m.decode_u32_at(bits, diff+self.m*i)?.0;
            }
            let count = count as usize + 2 - 1;
            Ok((
                GLZSym::Imm{
                    count: count,
                    imm: U::cast(imm)?
                },
                diff + countsize*self.m
            ))
        } else {
            // found an indirect reference
//            let refoffsize = (((sym >> self.l)
//                & (2u32.pow((Self::WIDTH-self.l) as u32)-1))
//                + 1) as usize;
            //let refoffsize = (sym >> (1 + Self::WIDTH)) + 0;
            let bound = (1 << Self::WIDTH as u32) + (1 << self.l as u32);
            let refoffsize = (sym / bound) + 0;
            //let refoffsize = (sym >> (Self::WIDTH)) - 1;
            //let refoffsize = (sym - (1 << Self::WIDTH)) >> self.l;
            let refsize = (((sym % bound) - (1 << Self::WIDTH)) + 2) as usize;

            let refoffsize = refoffsize as usize;
            let mut refoff = 0;
            for i in 0..refoffsize {
                refoff = (refoff << self.m) + 1
                    + self.m.decode_u32_at(bits, diff+self.m*i)?.0;
            }
            let refoff = refoff as usize - 1;
            Ok((
                GLZSym::Ref{off: refoff, size: refsize},
                diff + refoffsize*self.m
            ))
        }
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

    fn traverse_sym_raw<U: Sym, F: FnMut(U)>(
        &self,
        bits: &BitSlice,
        mut f: F,
    ) -> Result<usize> {
        // pass to our callback
        let (op, _) = self.rice.decode_u32(&bits)?;
        f(U::cast(op)?);

        // get size to skip
        let (_, diff) = self.decode_sym::<U>(&bits)?;
        Ok(diff)
    }

    fn traverse_sym<U: Sym, F: FnMut(U)>(
        &self,
        bits: &BitSlice,
        f: F,
    ) -> Result<usize> {
        self.traverse_sym_raw(bits, f)
            .chain_err(|| "could not decode GLZ symbol")
    }

    fn traverse_sym_at<U: Sym, F: FnMut(U)>(
        &self,
        bits: &BitSlice,
        off: usize,
        f: F,
    ) -> Result<usize> {
        self.traverse_sym(&bits[off..], f)
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
                        self.encode_sym::<U>(GLZSym::Ref{
                            off: *off-poff,
                            size: slice[i..j].len(),
                        }).ok()
                    )
                {
                    prefix = &slice[i..j];
                    pref = Some(nref);
                }
            }
            let prefconsume = prefix.len();

            let (pimm, pimmconsume) = {
//                let consume = 1;
                let mut i = j;
                let mut consume = 0;
                while i.checked_sub(1)
                    .and_then(|i| slice.get(i))
                    .filter(|c| **c == slice[j-1])
                    .is_some()
                {
                    i -= 1;
                    consume += 1;
                }

                (
                    self.encode_sym(GLZSym::Imm{count: consume, imm: slice[j-1]})?,
                    consume,
                )
            };

            // compare against a simple immediate
            //let imm = self.encode_sym(GLZSym::Imm{count: 1, imm: slice[j-1]})?;

            let consume: usize;
            let emit: usize;
            if forceimm || pref.as_ref().filter(|pref| {
                (pref.len() as f64 / prefconsume as f64) < (pimm.len() as f64 / pimmconsume as f64)
            }).is_none() {
                println!("imm {} {:?} -> {}", pimmconsume, &slice[j-pimmconsume..j], pimm);
                // not worth the overhead of the reference, emit immediate
                // but how manyy??
//                consume = 0;
//                let mut i = j;
//                while i.checked_sub(1)
//                    .and_then(|i| slice.get(i))
//                    .filter(|c| **c == slice[j-1])
//                    .is_some()
//                {
//                    i -= 1;
//                    consume += 1;
//                }
//                //consume = 1;
//
//                let imm = self.encode_sym(GLZSym::Imm{count: consume, imm: slice[j-1]})?;
                consume = pimmconsume;
                emit = pimm.len();
                patterns.push(pimm);
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
                println!("ref {} {:?} -> {}", prefix.len(), prefix, pref.as_ref().unwrap());
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
                (GLZSym::Imm{count, imm: x}, diff) => {
                    prog(count);
                    bytes.extend(iter::repeat(x).take(count));
                    off += diff;
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
            let diff = self.traverse_sym_at(&bits, off, &mut f)?;
            prog(1);
            off += diff;
        }

        Ok(())
    }
}

impl Encode for GLZ_ {
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

impl GranularEncode for GLZ_ {
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

//////////////////////////////////////////////////

#[derive(Debug)]
pub struct GLZ<E: SymEncode = GolombRice_> {
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
        GLZ::with_encoder(l, m, GLZ::DEFAULT_WIDTH,
            GolombRice_::new(GLZ::DEFAULT_WIDTH))
//        GLZ::with_encoder(l, m, GLZ::DEFAULT_WIDTH,
//            GolombRice::with_width(GLZ::DEFAULT_WIDTH+1, 16))
    }

    pub fn with_width(l: usize, m: usize, width: usize) -> GLZ {
        GLZ::with_encoder(l, m, width,
            GolombRice_::new(width))
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

    fn encode_sym_raw<U: Sym>(&self, sym: GLZSym<U>) -> Result<BitVec> {
        match sym {
            GLZSym::Imm{count, imm: x} => {
                let mut counts: Vec<usize> = Vec::new();
                let mut ncount = count + 1 - 2;
                while ncount != 0 {
                    ncount -= 1;
                    counts.push(ncount & (2usize.pow(self.m as u32)-1));
                    ncount >>= self.m;
                }
                counts.reverse();

                let countsize = counts.len();

                let imm: u32
                    = (0u32 << self.width)
                    | u32::cast(x)?;

                Ok(self.encoder.encode_u32(((countsize as u32 - 0) << (1+self.width as u32)) + imm)?.iter()
                    .chain(counts.iter()
                        .map(|&count| self.m.encode_u32(count as u32))
                        .collect::<Result<Vec<_>>>()?
                        .into_iter().flatten())
                    .collect())
            }
            GLZSym::Ref{off, size} => {
                ensure!(size >= 0+2 && size <= 2usize.pow(self.l as u32)-1+2,
                    "bad size {}", size);

                let mut offs: Vec<usize> = Vec::new();
                let mut noff = off + 1;
                while noff != 0 {
                    noff -= 1;
                    offs.push(noff & (2usize.pow(self.m as u32)-1));
                    noff >>= self.m;
                }
                offs.reverse();

                let offsize = offs.len();
//                ensure!(offsize >= 0+1 &&
//                    offsize <= 2usize.pow((self.width-self.l) as u32)-1+1,
//                    "bad offset {} (off = {})", offsize, off);

                let ref_: u32
                    = (1u32 << self.width)
//                    | ((self.width-self.l).cast_u32(offsize as u32 - 1)?
//                        << self.l)
                    | u32::cast(size as u32 - 2)?;

                Ok(self.encoder.encode_u32(((offsize as u32 - 0) << (/*1+*/self.width as u32)) + ref_)?.iter()
                    .chain(offs.iter()
                        .map(|&off| self.m.encode_u32(off as u32))
                        .collect::<Result<Vec<_>>>()?
                        .into_iter().flatten())
                    .collect())
            }
        }
    }

    fn encode_sym<U: Sym>(&self, sym: GLZSym<U>) -> Result<BitVec> {
        self.encode_sym_raw(sym)
            .chain_err(|| format!("could not encode GLZ symbol {:?}", sym))
    }

    fn decode_sym_raw<U: Sym>(
        &self,
        bits: &BitSlice
    ) -> Result<(GLZSym<U>, usize)> {
        // decode symbol
        let (sym, diff) = self.encoder.decode_u32(bits)
            .chain_err(|| format!("could not decode GLZ symbol"))?;

        //if sym & (1 << self.width) == 0 {
        if sym < (1 << self.width) {
            // found an immediate

            let countsize = (sym >> (1 + self.width)) + 0;
            let imm = sym & ((1 << self.width)-1);

            let countsize = countsize as usize;
            let mut count = 0;
            for i in 0..countsize {
                count = (count << self.m) + 1
                    + self.m.decode_u32_at(bits, diff+self.m*i)?.0;
            }
            let count = count as usize + 2 - 1;
            Ok((
                GLZSym::Imm{
                    count: count,
                    imm: U::cast(imm)?
                },
                diff + countsize*self.m
            ))
        } else {
            // found an indirect reference
//            let refoffsize = (((sym >> self.l)
//                & (2u32.pow((self.width-self.l) as u32)-1))
//                + 1) as usize;
            //let refoffsize = (sym >> (1 + self.width)) + 0;
            let refoffsize = (sym >> (self.width)) - 1 + 0;
            //let refoffsize = (sym - (1 << self.width)) >> self.l;
            let refsize = ((sym
                & (2u32.pow(self.l as u32)-1))
                + 2) as usize;

            let refoffsize = refoffsize as usize;
            let mut refoff = 0;
            for i in 0..refoffsize {
                refoff = (refoff << self.m) + 1
                    + self.m.decode_u32_at(bits, diff+self.m*i)?.0;
            }
            let refoff = refoff as usize - 1;
            Ok((
                GLZSym::Ref{off: refoff, size: refsize},
                diff + refoffsize*self.m
            ))
        }
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
            let mut prefix: &[U] = &[slice[j-1]];
            let mut pref: Option<BitVec> = None;
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
                    prefix = &slice[i..j];
                    pref = Some(nref);
                }
            }
            let prefconsume = prefix.len();

            let (pimm, pimmconsume) = {
                let consume = 1;
//                let mut i = j;
//                let mut consume = 0;
//                while i.checked_sub(1)
//                    .and_then(|i| slice.get(i))
//                    .filter(|c| **c == slice[j-1])
//                    .is_some()
//                {
//                    i -= 1;
//                    consume += 1;
//                }

                (
                    self.encode_sym(GLZSym::Imm{count: consume, imm: slice[j-1]})?,
                    consume,
                )
            };

            // compare against a simple immediate
            //let imm = self.encode_sym(GLZSym::Imm{count: 1, imm: slice[j-1]})?;

            let consume: usize;
            let emit: usize;
            if forceimm || pref.as_ref().filter(|pref| {
                (pref.len() as f64 / prefconsume as f64) < (pimm.len() as f64 / pimmconsume as f64)
            }).is_none() {
                // not worth the overhead of the reference, emit immediate
                // but how manyy??
//                consume = 0;
//                let mut i = j;
//                while i.checked_sub(1)
//                    .and_then(|i| slice.get(i))
//                    .filter(|c| **c == slice[j-1])
//                    .is_some()
//                {
//                    i -= 1;
//                    consume += 1;
//                }
//                //consume = 1;
//
//                let imm = self.encode_sym(GLZSym::Imm{count: consume, imm: slice[j-1]})?;
                consume = pimmconsume;
                emit = pimm.len();
                patterns.push(pimm);
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
                (GLZSym::Imm{count, imm: x}, diff) => {
                    prog(count);
                    bytes.extend(iter::repeat(x).take(count));
                    off += diff;
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
        f: F,
        prog: (impl FnMut(usize), impl FnMut(usize)),
    ) -> Result<()> {
        let (bits, _) = self.encode_all_with_prog(slices, prog)?;
        self.traverse_syms(&bits, f)
//
//
//        let mut off = 0;
//        while off < bits.len() {
//            let (op, _) = self.encoder.decode_u32_at(&bits, off)?;
//
//            // pass to our callback
//            f(V::cast(op & ((1<<(1+self.width))-1))?);
//
//            // get size to skip
//            let (_, diff) = self.decode_sym_at::<U>(&bits, off)?;
//            off += diff;
//        }
//
//        Ok(())
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
            let (op, _) = self.encoder.decode_u32_at(&bits, off)?;

            // pass to our callback
            prog(1);
            f(U::cast(op)?);

            // get size to skip
            let (_, diff) = self.decode_sym_at::<U>(&bits, off)?;
            off += diff;
        }

        Ok(())
    }


//
//    pub fn traverse_syms_with_prog<U: Sym, F: FnMut(U)>(&self, bits: &BitSlice) {
//        
//    }
//
//
//    fn traverse_syms_all<U: Sym>(
//        &self,
//        bits: &BitSlice,
//        offs: &[(usize, usize)]
//    ) -> Result<Vec<Vec<U>>> {
//        self.traverse_syms_all_with_prog(bits, offs, (|_|(), |_|()))
//    }
//
//    fn traverse_syms_at<U: Sym>(
//        &self,
//        bits: &BitSlice,
//        off: usize,
//        len: usize
//    ) -> Result<Vec<U>> {
//        self.traverse_syms_at_with_prog(bits, off, len, |_|())
//    }
//
//    fn traverse_syms_all_with_prog<U: Sym>(
//        &self,
//        bits: &BitSlice,
//        offs: &[(usize, usize)],
//        mut prog: (impl FnMut(usize), impl FnMut(usize)),
//    ) -> Result<Vec<Vec<U>>> {
//        offs.iter().map(|(off, len)| {
//            let slice = self.traverse_syms_at_with_prog(bits, *off, *len, &mut prog.1);
//            prog.0(1);
//            slice
//        }).collect()
//    }
//
//    fn traverse_syms_at_with_prog<U: Sym>(
//        &self,
//        bits: &BitSlice,
//        mut off: usize,
//        len: usize,
//        prog: impl FnMut(usize),
//    ) -> Result<Vec<U>> {
//        while off < bits.len() {
//            let (op, _) = self.encoder.decode_u32_at(&bits, off)?;
//
//            // pass to our callback
//            f(V::cast(op & ((1<<(1+self.width))-1))?);
//
//            // get size to skip
//            let (_, diff) = self.decode_sym_at::<U>(&bits, off)?;
//            off += diff;
//        }
//
//        Ok(())
//    }

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
        let glz = GLZ_::with_config(8, 5, 3);
        assert_eq!(
            glz.encode_sym::<u8>(GLZSym::Imm{count: 1, imm: b'a'})?,
            bitvec![
                0, 0,1,1,0,0,0,0,1
            ]
        );
        let glz = GLZ_::with_config(8, 5, 3);
        assert_eq!(
            glz.encode_sym::<u8>(GLZSym::Imm{count: 2, imm: b'a'})?,
            bitvec![
                1,0, 1,0,0,0,0,0,0,1,
                0,0,0,
            ]
        );
        let glz = GLZ_::with_config(8, 5, 3);
        assert_eq!(
            glz.encode_sym::<u8>(GLZSym::Imm{count: 11, imm: b'a'})?,
            bitvec![
                1,1,0, 1,0,1,0,0,0,0,1,
                0,0,0, 0,0,1,
            ]
        );

        Ok(())
    }

    #[test]
    fn encode_ref_test() -> Result<()> {
        let glz = GLZ_::with_config(8, 5, 3);
        assert_eq!(
            glz.encode_sym::<u8>(GLZSym::Ref{off:21, size:12})?,
            bitvec![
                1,1,1,0, 0,1,0,0,1,0,1,0,
                0,0,1, 1,0,1,
            ]
        );
        let glz = GLZ_::with_config(8, 7, 7);
        assert_eq!(
            glz.encode_sym::<u8>(GLZSym::Ref{off:21, size:12})?,
            bitvec![
                1,1,0, 1,0,0,0,1,0,1,0,
                0,0,1,0,1,0,1,
            ]
        );
        let glz = GLZ_::with_config(8, 8, 8);
        assert_eq!(
            glz.encode_sym::<u8>(GLZSym::Ref{off:21, size:12})?,
            bitvec![
                1,1,1,0, 0,0,0,0,1,0,1,0,
                0,0,0,1,0,1,0,1,
            ]
        );
        let glz = GLZ_::with_config(8, 4, 1);
        assert_eq!(
            glz.encode_sym::<u8>(GLZSym::Ref{off:21, size:12})?,
            bitvec![
                1,1,1,1,1,0, 0,1,0,0,1,0,1,0,
                0,1,1,1,
            ]
        );

        Ok(())
    }

    #[test]
    fn sym_symmetry_test() -> Result<()> {
        let glz = GLZ_::with_config(8, 5, 3);
        let sym = GLZSym::Imm{count: 1, imm: b'a'};
        assert_eq!(
            glz.decode_sym::<u8>(&glz.encode_sym::<u8>(sym)?)?,
            (sym, 9)
        );
        let sym = GLZSym::Imm{count: 2, imm: b'a'};
        assert_eq!(
            glz.decode_sym::<u8>(&glz.encode_sym::<u8>(sym)?)?,
            (sym, 13)
        );
        let sym = GLZSym::Imm{count: 11, imm: b'a'};
        assert_eq!(
            glz.decode_sym::<u8>(&glz.encode_sym::<u8>(sym)?)?,
            (sym, 17)
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
        let glz = GLZ_::with_config(8, 5, 3);
        assert_eq!(glz.encode(b"hello world!")?.len(), 103);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(b"hello world!")?)?,
            b"hello world!".to_vec()
        );

        let phrase = b"hello world hello hello world!";
        assert_eq!(glz.encode(phrase)?.len(), 144);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let phrase = b"hhhhh wwwww hhhhh hhhhh wwwww!";
        assert_eq!(glz.encode(phrase)?.len(), 85);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let phrase = b"hhhhh hhhhh hhhhh hhhhh hhhhh!";
        assert_eq!(glz.encode(phrase)?.len(), 94);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let phrase = b"hhhhhhhhhhhhhhhhhhhhhhhhhhhhh!";
        assert_eq!(glz.encode(phrase)?.len(), 26);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let phrase = b"hhhhhhhhhhhhhhhhhhhhhhhhhhhhhh";
        assert_eq!(glz.encode(phrase)?.len(), 17);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        Ok(())
    }

    #[test]
    fn seeded_symmetry_test() -> Result<()> {
        let phrase = b"hello world!";
        let glz = GLZ_::from_seed(None, 5, 3, phrase.iter().copied());
        assert_eq!(glz.k(), 4);
        assert_eq!(glz.encode(phrase)?.len(), 76);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let phrase = b"hello world hello hello world!";
        let glz = GLZ_::from_seed(None, 5, 3, phrase.iter().copied());
        assert_eq!(glz.k(), 6);
        assert_eq!(glz.encode(phrase)?.len(), 127);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let phrase = b"hhhhh wwwww hhhhh hhhhh wwwww!";
        let glz = GLZ_::from_seed(None, 5, 3, phrase.iter().copied());
        assert_eq!(glz.k(), 7);
        assert_eq!(glz.encode(phrase)?.len(), 81);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let phrase = b"hhhhh hhhhh hhhhh hhhhh hhhhh!";
        let glz = GLZ_::from_seed(None, 5, 3, phrase.iter().copied());
        assert_eq!(glz.k(), 7);
        assert_eq!(glz.encode(phrase)?.len(), 89);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let phrase = b"hhhhhhhhhhhhhhhhhhhhhhhhhhhhh!";
        let glz = GLZ_::from_seed(None, 5, 3, phrase.iter().copied());
        assert_eq!(glz.k(), 7);
        assert_eq!(glz.encode(phrase)?.len(), 26);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let phrase = b"hhhhhhhhhhhhhhhhhhhhhhhhhhhhhh";
        let glz = GLZ_::from_seed(None, 5, 3, phrase.iter().copied());
        assert_eq!(glz.k(), 8);
        assert_eq!(glz.encode(phrase)?.len(), 17);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        Ok(())
    }
}
