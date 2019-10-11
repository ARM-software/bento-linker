use std::rc::Rc;

use crate::bits::*;
use crate::errors::*;
use crate::glz::GLZ;
use crate::rice::GolombRice;

// Combination of GLZ and Rice codes
//
// Provides near DEFLATE-like compression by benefiting from both
// pattern-based and symbol-based compression

#[derive(Debug)]
pub struct GLZoR {
    glz: GLZ<Rc<GolombRice>>,
    rice: Rc<GolombRice>,
}

impl GLZoR {
    pub const DEFAULT_L: usize     = GLZ::DEFAULT_L;
    pub const DEFAULT_M: usize     = GLZ::DEFAULT_M;
    pub const DEFAULT_WIDTH: usize = GLZ::DEFAULT_WIDTH;

    pub fn new(k: usize, l: usize, m: usize) -> GLZoR {
        GLZoR::with_width(k, l, m, GLZoR::DEFAULT_WIDTH)
    }

    pub fn with_width(k: usize, l: usize, m: usize, width: usize) -> GLZoR {
        let rice = Rc::new(GolombRice::with_width(k, 1+width));
        GLZoR{
            glz: GLZ::with_encoder(l, m, width, Rc::clone(&rice)),
            rice: rice,
        }
    }

    pub fn with_table<U: Sym>(
        k: usize,
        l: usize,
        m: usize,
        width: usize,
        decode_table: &[U],
    ) -> GLZoR {
        let rice = Rc::new(GolombRice::with_table(k, 1+width, decode_table));
        GLZoR{
            glz: GLZ::with_encoder(l, m, width, Rc::clone(&rice)),
            rice: rice,
        }
    }

    pub fn from_hist(
        k: Option<usize>,
        l: usize,
        m: usize,
        width: usize,
        hist: &[usize],
    ) -> GLZoR {
        let rice = Rc::new(GolombRice::from_hist(k, 1+width, hist));
        GLZoR{
            glz: GLZ::with_encoder(l, m, width, Rc::clone(&rice)),
            rice: rice,
        }
    }

    pub fn from_seed<I, U>(
        k: Option<usize>,
        l: usize,
        m: usize,
        width: usize,
        seed: I,
    ) -> GLZoR
    where
        I: IntoIterator<Item=U>,
        U: Sym,
    {
        GLZoR::from_seed_all(k, l, m, width,
            &[&seed.into_iter().collect::<Vec<_>>()])
    }

    pub fn from_seed_all<U: Sym>(
        k: Option<usize>,
        l: usize,
        m: usize,
        width: usize,
        seeds: &[&[U]],
    ) -> GLZoR {
        GLZoR::from_seed_all_with_prog(k, l, m, width,
            seeds, (|_|(), |_|()))
    }

    pub fn from_seed_all_with_prog<U: Sym>(
        k: Option<usize>,
        l: usize,
        m: usize,
        width: usize,
        seeds: &[&[U]],
        prog: (impl FnMut(usize), impl FnMut(usize)),
    ) -> GLZoR {
        let glz = GLZ::with_width(l, m, width);
        let mut hist: Vec<usize> = vec![0; 2usize.pow(1+width as u32)];
        glz.map_ops_all_with_prog(&seeds, |op: u32| {
            hist[op as usize] += 1;
        }, prog).ok();

        GLZoR::from_hist(k, l, m, width, &hist)
    }

    pub fn k(&self) -> usize {
        self.rice.k()
    }

    pub fn l(&self) -> usize {
        self.glz.l()
    }

    pub fn m(&self) -> usize {
        self.glz.m()
    }

    pub fn width(&self) -> usize {
        self.glz.width()
    }

    pub fn encode_table<U: Sym>(&self) -> Option<Vec<U>> {
        self.rice.encode_table()
    }

    pub fn decode_table<U: Sym>(&self) -> Option<Vec<U>> {
        self.rice.decode_table()
    }
}

impl Encode for GLZoR {
    fn encode_with_prog<U: Sym>(
        &self,
        bytes: &[U],
        prog: impl FnMut(usize),
    ) -> Result<BitVec> {
        self.glz.encode_with_prog(bytes, prog)
    }

    fn decode_with_prog<U: Sym>(
        &self,
        bits: &BitSlice,
        prog: impl FnMut(usize)
    ) -> Result<Vec<U>> {
        self.glz.decode_with_prog(bits, prog)
    }
}

impl GranularEncode for GLZoR {
    fn encode_all_with_prog<U: Sym>(
        &self,
        slices: &[&[U]],
        prog: (impl FnMut(usize), impl FnMut(usize)),
    ) -> Result<(BitVec, Vec<(usize, usize)>)> {
        self.glz.encode_all_with_prog(slices, prog)
    }

    fn decode_at_with_prog<U: Sym>(
        &self,
        bits: &BitSlice,
        off: usize,
        len: usize,
        prog: impl FnMut(usize),
    ) -> Result<Vec<U>> {
        self.glz.decode_at_with_prog(bits, off, len, prog)
    }
}


#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn symmetry_test() -> Result<()> {
        let phrase = b"hello world!";
        let glz = GLZoR::from_seed(None, 5, 3, 8, phrase.iter().copied());
        assert_eq!(glz.k(), 1);
        assert_eq!(glz.encode(phrase)?.len(), 40);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let phrase = b"hello world hello hello world!";
        let glz = GLZoR::from_seed(None, 5, 3, 8, phrase.iter().copied());
        assert_eq!(glz.k(), 2);
        assert_eq!(glz.encode(phrase)?.len(), 64);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let phrase = b"hhhhh wwwww hhhhh hhhhh wwwww!";
        let glz = GLZoR::from_seed(None, 5, 3, 8, phrase.iter().copied());
        assert_eq!(glz.k(), 2);
        assert_eq!(glz.encode(phrase)?.len(), 282);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let phrase = b"hhhhh hhhhh hhhhh hhhhh hhhhh!";
        let glz = GLZoR::from_seed(None, 5, 3, 8, phrase.iter().copied());
        assert_eq!(glz.k(), 2);
        assert_eq!(glz.encode(phrase)?.len(), 153);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let phrase = b"hhhhhhhhhhhhhhhhhhhhhhhhhhhhh!";
        let glz = GLZoR::from_seed(None, 5, 3, 8, phrase.iter().copied());
        assert_eq!(glz.k(), 2);
        assert_eq!(glz.encode(phrase)?.len(), 134);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        let phrase = b"hhhhhhhhhhhhhhhhhhhhhhhhhhhhhh";
        let glz = GLZoR::from_seed(None, 5, 3, 8, phrase.iter().copied());
        assert_eq!(glz.k(), 1);
        assert_eq!(glz.encode(phrase)?.len(), 62);
        assert_eq!(
            glz.decode::<u8>(&glz.encode(phrase)?)?,
            phrase.to_vec()
        );

        Ok(())
    }
}
