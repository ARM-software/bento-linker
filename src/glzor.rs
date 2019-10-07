use std::iter;
use std::rc::Rc;

use super::bits::*;
use super::glz::GLZ;
use super::rice::GolombRice;


// Combination of GLZ and Rice codes
//
// Provides near DEFLATE-like compression by benefiting from both
// pattern-based and symbol-based compression

struct GLZoR {
    glz: GLZ<Rc<GolombRice>>,
    rice: Rc<GolombRice>,
}

impl<T: SymEncode> SymEncode for Rc<T> {
    fn encode_sym<U: Sym>(          
        &self,                      
        n: U                        
    ) -> Result<BitVec, String> { 
        (**self).encode_sym(n)
    }

    fn decode_sym<U: Sym>(          
        &self,                      
        bits: &BitSlice             
    ) -> Result<(U, usize), String> {
        (**self).decode_sym(bits)
    }
}

impl GLZoR {
    #[allow(dead_code)]
    pub fn new(k: usize, l: usize, m: usize) -> GLZoR {
        GLZoR::with_width(k, l, m, 8)
    }

    #[allow(dead_code)]
    pub fn with_width(k: usize, l: usize, m: usize, width: usize) -> GLZoR {
        let rice = Rc::new(GolombRice::with_width(k, 1+width));
        GLZoR{
            glz: GLZ::with_encoder(l, m, width, Rc::clone(&rice)),
            rice: rice,
        }
    }

    #[allow(dead_code)]
    pub fn with_table<U: Sym>(
        k: usize,
        l: usize,
        m: usize,
        width: usize,
        table: &[U],
    ) -> GLZoR {
        let rice = Rc::new(GolombRice::with_table(k, 1+width, table));
        GLZoR{
            glz: GLZ::with_encoder(l, m, width, Rc::clone(&rice)),
            rice: rice,
        }
    }

    #[allow(dead_code)]
    #[allow(unused_variables)]
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

    #[allow(dead_code)]
    #[allow(unused_variables)]
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
        GLZoR::from_seed_all(k, l, m, width, iter::once(seed))
    }

    #[allow(dead_code)]
    #[allow(unused_variables)]
    pub fn from_seed_all<II, I, U>(
        k: Option<usize>,
        l: usize,
        m: usize,
        width: usize,
        seeds: II,
    ) -> GLZoR
    where
        II: IntoIterator<Item=I>,
        I: IntoIterator<Item=U>,
        U: Sym,
    {
        // TODO do this better
        let seeds: Vec<Vec<U>> = seeds.into_iter().map(
            |x| x.into_iter().collect()
        ).collect();
        let seeds: &[&[U]] = &seeds.iter()
            .map(|x| x.as_slice())
            .collect::<Vec<&[U]>>();

        let glz = GLZ::with_width(l, m, width);
        let mut hist: Vec<usize> = vec![0; 2usize.pow(1+width as u32)];
        glz.map_ops_all(seeds, |op: u32| {
            hist[op as usize] += 1;
        }).ok();

        GLZoR::from_hist(k, l, m, width, &hist)
    }

    #[allow(dead_code)]
    pub fn k(&self) -> usize {
        self.rice.k()
    }

    #[allow(dead_code)]
    pub fn l(&self) -> usize {
        self.glz.l()
    }

    #[allow(dead_code)]
    pub fn m(&self) -> usize {
        self.glz.m()
    }

    #[allow(dead_code)]
    pub fn width(&self) -> usize {
        self.rice.width()
    }

    #[allow(dead_code)]
    pub fn table<U: Sym>(&self) -> Option<Vec<U>> {
        self.rice.table()
    }

    #[allow(dead_code)]
    pub fn reverse_table<U: Sym>(&self) -> Option<Vec<U>> {
        self.rice.reverse_table()
    }
}

impl Encode for GLZoR {
    fn encode<U: Sym>(&self, bytes: &[U]) -> Result<BitVec, String> {
        self.glz.encode(bytes)
    }

    fn decode<U: Sym>(&self, bits: &BitSlice) -> Result<Vec<U>, String> {
        self.glz.decode(bits)
    }
}

impl GranularEncode for GLZoR {
    fn encode_all<U: Sym>(
        &self,
        slices: &[&[U]]
    ) -> Result<(BitVec, Vec<(usize, usize)>), String> {
        self.glz.encode_all(slices)
    }

    fn decode_at<U: Sym>(
        &self,
        bits: &BitSlice,
        off: usize,
        len: usize
    ) -> Result<Vec<U>, String> {
        self.glz.decode_at(bits, off, len)
    }
}


#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn symmetry_test() {
        let phrase = b"hello world!";
        let glz = GLZoR::from_seed(None, 5, 3, 8, phrase.iter().copied());
        assert_eq!(glz.k(), 1);
        assert_eq!(glz.encode(phrase).unwrap().len(), 40);
        assert_eq!(
            glz.decode(&glz.encode(phrase).unwrap()),
            Ok(phrase.to_vec())
        );

        let phrase = b"hello world hello hello world!";
        let glz = GLZoR::from_seed(None, 5, 3, 8, phrase.iter().copied());
        assert_eq!(glz.k(), 2);
        assert_eq!(glz.encode(phrase).unwrap().len(), 64);
        assert_eq!(
            glz.decode(&glz.encode(phrase).unwrap()),
            Ok(phrase.to_vec())
        );

        let phrase = b"hhhhh wwwww hhhhh hhhhh wwwww!";
        let glz = GLZoR::from_seed(None, 5, 3, 8, phrase.iter().copied());
        assert_eq!(glz.k(), 2);
        assert_eq!(glz.encode(phrase).unwrap().len(), 282);
        assert_eq!(
            glz.decode(&glz.encode(phrase).unwrap()),
            Ok(phrase.to_vec())
        );

        let phrase = b"hhhhh hhhhh hhhhh hhhhh hhhhh!";
        let glz = GLZoR::from_seed(None, 5, 3, 8, phrase.iter().copied());
        assert_eq!(glz.k(), 2);
        assert_eq!(glz.encode(phrase).unwrap().len(), 153);
        assert_eq!(
            glz.decode(&glz.encode(phrase).unwrap()),
            Ok(phrase.to_vec())
        );

        let phrase = b"hhhhhhhhhhhhhhhhhhhhhhhhhhhhh!";
        let glz = GLZoR::from_seed(None, 5, 3, 8, phrase.iter().copied());
        assert_eq!(glz.k(), 2);
        assert_eq!(glz.encode(phrase).unwrap().len(), 134);
        assert_eq!(
            glz.decode(&glz.encode(phrase).unwrap()),
            Ok(phrase.to_vec())
        );

        let phrase = b"hhhhhhhhhhhhhhhhhhhhhhhhhhhhhh";
        let glz = GLZoR::from_seed(None, 5, 3, 8, phrase.iter().copied());
        assert_eq!(glz.k(), 1);
        assert_eq!(glz.encode(phrase).unwrap().len(), 62);
        assert_eq!(
            glz.decode(&glz.encode(phrase).unwrap()),
            Ok(phrase.to_vec())
        );
    }
}
