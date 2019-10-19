use std::iter;

use crate::bits::*;
use crate::errors::*;
use crate::hist::Hist;


//// Golomb-Rice code conversions
#[derive(Debug, Clone)]
pub struct GolombRice_ {
    k: usize,
}

impl GolombRice_ {
    pub fn new(k: usize) -> Self {
        Self{k: k}
    }

    pub fn from_hist(hist: &Hist) -> Self {
        // find best k from our histogram, this
        // assumes the histogram will be used with
        // the Golomb Rice encoding in a BijectEncoderr
        let bound = hist.bound() as u32;
        if bound == 0 {
            return Self::new(0);
        }

        let bound = 32 - (bound-1).leading_zeros();
        let k = (0..=bound as usize).map(|k| {
            let gr = Self::new(k);
            let size: usize = hist.iter::<u32>().map(|(n, c)| {
                c * gr.encode_sym(n).unwrap().len()
            }).sum();
            (size, k)
        }).min().unwrap().1;

        Self::new(k)
    }

    pub fn from_seed<I: IntoIterator<Item=U>, U: Sym>(seed: I) -> Self {
        let mut hist = Hist::new();
        for x in seed {
            hist.increment(x);
        }

        Self::from_hist(&hist)
    }

    pub fn k(&self) -> usize {
        self.k
    }
}

impl SymEncode for GolombRice_ {
    fn encode_sym<U: Sym>(&self, n: U) -> Result<BitVec> {
        let (m, n) = (1u32 << (self.k as u32), n.into());
        let (q, r) = (n/m, n%m);
        Ok(iter::repeat(true).take(q as usize)
            .chain(iter::once(false))
            .chain(self.k.encode_sym(r)?)
            .collect())
    }

    fn decode_sym<U: Sym>(&self, rice: &BitSlice) -> Result<(U, usize)> {
        let m = 1u32 << (self.k as u32);
        let q = rice.iter().position(|b| b == false)
            .ok_or("unterminated rice code")?;
        let r = self.k.decode_u32_at(rice, q+1)?.0;
        Ok((U::cast(q as u32*m+r)?, q+1+self.k))
    }
}


#[derive(Debug)]
pub struct GolombRice {
    k: usize,
    width: usize,
    table: Option<(Vec<u32>, Vec<u32>)>,
}

fn table_cast<U: Sym, V:Sym>(
    table: &[U]
) -> Result<Vec<V>> {
    table.iter().map(|&n| V::cast(n)).collect()
}

fn reverse_table(table: &[u32]) -> Vec<u32> {
    let mut reverse_table = vec![0; table.len()];
    for (i, &n) in table.iter().enumerate() {
        reverse_table[n as usize] = i as u32;
    }
    reverse_table
}

impl GolombRice {
    pub const DEFAULT_K: usize      = 5;
    pub const DEFAULT_WIDTH: usize  = 8;

    pub fn new(k: usize) -> GolombRice {
        GolombRice{k: k, width: GolombRice::DEFAULT_WIDTH, table: None}
    }

    pub fn with_width(k: usize, width: usize) -> GolombRice {
        GolombRice{k: k, width: width, table: None}
    }

    pub fn with_table<U: Sym>(
        k: usize,
        width: usize,
        decode_table: &[U]
    ) -> GolombRice {
        assert!(decode_table.len() <= 2usize.pow(width as u32));
        let decode_table: Vec<u32> = table_cast(decode_table).unwrap();
        let encode_table = reverse_table(&decode_table);

        GolombRice{
            k: k,
            width: width,
            table: Some((
                encode_table,
                decode_table,
            )),
        }
    }

    pub fn from_hist(
        k: Option<usize>,
        width: usize,
        hist: &Hist,
    ) -> GolombRice {
        // build tables
        let mut hist = hist.clone();
        hist.sort();
        let encode_table = hist.encode_table().unwrap();
        let decode_table = hist.decode_table().unwrap();

        // either use provided k, or find best k for our histogram
        let k = k.unwrap_or_else(||
           (0..=width).map(|k| {
                let gr = GolombRice::with_width(k, width);
                let size: usize = hist.iter::<u32>().map(|(n, c)|
                    c * gr.encode_sym(n)
                        .unwrap().len()
                ).sum();
                (size, k)
            }).min().unwrap().1);

        GolombRice{
            k: k,
            width: width,
            table: Some((
                encode_table,
                decode_table,
            )),
        }
    }

    pub fn from_seed<I, U>(
        k: Option<usize>,
        width: usize,
        seed: I
    ) -> GolombRice
    where
        I: IntoIterator<Item=U>,
        U: Sym,
    {
        // build up histogram
        GolombRice::from_hist(k, width, &Hist::from_seed(seed))
    }

    pub fn k(&self) -> usize {
        self.k
    }

    pub fn width(&self) -> usize {
        self.width
    }

    pub fn encode_table<U: Sym>(&self) -> Option<Vec<U>> {
        self.table.as_ref().map(|(t, _)| table_cast(t).unwrap())
    }

    pub fn decode_table<U: Sym>(&self) -> Option<Vec<U>> {
        self.table.as_ref().map(|(_, t)| table_cast(t).unwrap())
    }
}

impl SymEncode for GolombRice {
    fn encode_sym<U: Sym>(&self, n: U) -> Result<BitVec> {
        let mut n = n.into();
        if let Some((encode_table, decode_table)) = &self.table {
            let top = n >> (1+self.width);
            let bot = n % decode_table.len() as u32;
            n = encode_table[bot as usize]
                | (top * (decode_table.len() as u32))
        }

        if self.k < self.width {
            let m = 1u32 << (self.k as u32);
            let (q, r) = (n/m, n%m);
            Ok(iter::repeat(true).take(q as usize)
                .chain(iter::once(false))
                .chain(self.k.encode_sym(r)?)
                .collect())
        } else {
            self.width.encode_sym(n)
        }
    }

    fn decode_sym<U: Sym>(&self, rice: &BitSlice) -> Result<(U, usize)> {
        let (mut n, diff) = if self.k < self.width {
            let m = 1u32 << (self.k as u32);
            let q = rice.iter().position(|b| b == false)
                .ok_or("unterminated rice code")?;
            let r = self.k.decode_u32_at(rice, q+1)?.0;
            (q as u32*m+r, q+1+self.k)
        } else {
            self.width.decode_u32(rice)?
        };

        if let Some((_, decode_table)) = &self.table {
            let top = n / decode_table.len() as u32;
            let bot = n % decode_table.len() as u32;
            n = decode_table[bot as usize]
                | (top << (1+self.width))
        }

        Ok((U::cast(n)?, diff))
    }
}


// Tests
#[cfg(test)]
mod tests {
    use super::*;
    use crate::hist::BijectEncoder;

    impl SymEncode for &GolombRice_ {
        fn encode_sym<U: Sym>(&self, n: U) -> Result<BitVec> {
            (**self).encode_sym(n)
        }

        fn decode_sym<U: Sym>(&self, bits: &BitSlice) -> Result<(U, usize)> {
            (**self).decode_sym(bits)
        }
    }

    #[test]
    fn encode_test() -> Result<()> {
        assert_eq!(
            GolombRice_::new(8).encode_u8(0b01011100u8)?,
            bitvec![0,0,1,0,1,1,1,0,0]
        );
        assert_eq!(
            GolombRice_::new(7).encode_u8(0b01011100u8)?,
            bitvec![0,1,0,1,1,1,0,0]
        );
        assert_eq!(
            GolombRice_::new(6).encode_u8(0b01011100u8)?,
            bitvec![1,0,0,1,1,1,0,0]
        );
        assert_eq!(
            GolombRice_::new(5).encode_u8(0b01011100u8)?,
            bitvec![1,1,0,1,1,1,0,0]
        );
        assert_eq!(
            GolombRice_::new(4).encode_u8(0b01011100u8)?,
            bitvec![1,1,1,1,1,0,1,1,0,0]
        );
        assert_eq!(
            GolombRice_::new(3).encode_u8(0b01011100u8)?,
            bitvec![1,1,1,1,1,1,1,1,1,1,1,0,1,0,0]
        );
        assert_eq!(
            GolombRice_::new(2).encode_u8(0b01011100u8)?,
            bitvec![
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0
            ]
        );
        assert_eq!(
            GolombRice_::new(1).encode_u8(0b01011100u8)?,
            bitvec![
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0
            ]
        );
        assert_eq!(
            GolombRice_::new(0).encode_u8(0b01011100u8)?,
            bitvec![
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0]
        );

        Ok(())
    }

    #[test]
    fn decode_test() -> Result<()> {
        assert_eq!(
            GolombRice_::new(8).decode_u8(&bitvec![0,0,1,0,1,1,1,0,0])?,
            (0b01011100u8, 9)
        );
        assert_eq!(
            GolombRice_::new(7).decode_u8(&bitvec![0,1,0,1,1,1,0,0])?,
            (0b01011100u8, 8)
        );
        assert_eq!(
            GolombRice_::new(6).decode_u8(&bitvec![1,0,0,1,1,1,0,0])?,
            (0b01011100u8, 8)
        );
        assert_eq!(
            GolombRice_::new(5).decode_u8(&bitvec![1,1,0,1,1,1,0,0])?,
            (0b01011100u8, 8)
        );
        assert_eq!(
            GolombRice_::new(4).decode_u8(&bitvec![1,1,1,1,1,0,1,1,0,0])?,
            (0b01011100u8, 10)
        );
        assert_eq!(
            GolombRice_::new(3).decode_u8(&bitvec![
                1,1,1,1,1,1,1,1,1,1,1,0,1,0,0
            ])?,
            (0b01011100u8, 15)
        );
        assert_eq!(
            GolombRice_::new(2).decode_u8(&bitvec![
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0
            ])?,
            (0b01011100u8, 23+3)
        );
        assert_eq!(
            GolombRice_::new(1).decode_u8(&bitvec![
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0
            ])?,
            (0b01011100u8, 2*23+2)
        );
        assert_eq!(
            GolombRice_::new(0).decode_u8(&bitvec![
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0
            ])?,
            (0b01011100u8, 4*23+1)
        );

        Ok(())
    }

    #[test]
    fn errors_test() -> Result<()> {
        assert!(GolombRice_::new(4)
            .decode_u8(&bitvec![1,1,1,1,1,1,1,1]).is_err());
        assert!(GolombRice_::new(4)
            .decode_u8(&bitvec![1,1,1,0]).is_err());
        assert!(GolombRice_::new(4)
            .decode_u8(&bitvec![]).is_err());

        Ok(())
    }

    #[test]
    fn rice_symmetry_test() -> Result<()> {
        for i in 0..8 {
            let gr = GolombRice_::new(i);
            assert_eq!(
                gr.decode_u8(&gr.encode_u8(b'h')?).map(|(n,_)| n)?,
                b'h'
            );
            assert_eq!(
                gr.decode::<u8>(&gr.encode(b"hello world!")?)?,
                b"hello world!".to_vec()
            );
        }

        Ok(())
    }

    #[test]
    fn hist_k_test() -> Result<()> {
        let gr = GolombRice_::from_seed(
            [0u8;0].iter().copied());
        assert_eq!(gr.k(), 0);

        let gr = GolombRice_::from_seed(
            [0u8;100].iter().copied());
        assert_eq!(gr.k(), 0);

        let gr = GolombRice_::from_seed(
            iter::repeat(0u8).take(100));
        assert_eq!(gr.k(), 0);

        let gr = GolombRice_::from_seed(
            0..=255u8);
        assert_eq!(gr.k(), 6);

        let gr = GolombRice_::from_seed(
            (0..=255u8).chain(iter::repeat(0u8).take(1000)));
        assert_eq!(gr.k(), 4);

        Ok(())
    }

    #[test]
    fn hist_symmetry_test() -> Result<()> {
        let mut hist = Hist::from_seed(b"hello world!".iter().copied());
        hist.sort();
        let gr = BijectEncoder::new(GolombRice_::from_hist(&hist), hist);
        assert_eq!(gr.encoder().k(), 1);
        assert_eq!(
            gr.encode_u8(b'h')?,
            bitvec![1,1,1,0,0]
        );
        assert_eq!(
            gr.decode_u8(&gr.encode_u8(b'h')?)?,
            (b'h', 5)
        );
        assert_eq!(
            gr.encode(b"hello world!").map(|x| x.len())?,
            40
        );
        assert_eq!(
            gr.decode::<u8>(&gr.encode(b"hello world!")?)?,
            b"hello world!".to_vec()
        );

        let mut hist = Hist::from_seed(b"hhhhh world!".iter().copied());
        hist.sort();
        let gr = BijectEncoder::new(GolombRice_::from_hist(&hist), hist);
        assert_eq!(gr.encoder().k(), 1);
        assert_eq!(
            gr.encode_u8(b'h')?,
            bitvec![0,0]
        );
        assert_eq!(
            gr.decode_u8(&gr.encode_u8(b'h')?)?, 
            (b'h', 2)
        );
        assert_eq!(
            gr.encode(b"hhhhh world!").map(|x| x.len())?,
            36
        );
        assert_eq!(
            gr.decode::<u8>(&gr.encode(b"hhhhh world!")?)?,
            b"hhhhh world!".to_vec()
        );

        let mut hist = Hist::from_seed(b"hhhhhhhhhhh!".iter().copied());
        hist.sort();
        let gr = BijectEncoder::new(GolombRice_::from_hist(&hist), hist);
        assert_eq!(gr.encoder().k(), 0);
        assert_eq!(
            gr.encode_u8(b'h')?,
            bitvec![0]
        );
        assert_eq!(
            gr.decode_u8(&gr.encode_u8(b'h')?)?, 
            (b'h', 1)
        );
        assert_eq!(
            gr.encode(b"hhhhhhhhhhh!").map(|x| x.len())?,
            13
        );
        assert_eq!(
            gr.decode::<u8>(&gr.encode(b"hhhhhhhhhhh!")?)?,
            b"hhhhhhhhhhh!".to_vec()
        );

        let mut hist = Hist::from_seed(b"hhhhhhhhhhhh".iter().copied());
        hist.sort();
        let gr = BijectEncoder::new(GolombRice_::from_hist(&hist), hist);
        assert_eq!(gr.encoder().k(), 0);
        assert_eq!(
            gr.encode_u8(b'h')?,
            bitvec![0]
        );
        assert_eq!(
            gr.decode_u8(&gr.encode_u8(b'h')?)?, 
            (b'h', 1)
        );
        assert_eq!(
            gr.encode(b"hhhhhhhhhhhh").map(|x| x.len())?,
            12
        );
        assert_eq!(
            gr.decode::<u8>(&gr.encode(b"hhhhhhhhhhhh")?)?,
            b"hhhhhhhhhhhh".to_vec()
        );

        Ok(())
    }
}
