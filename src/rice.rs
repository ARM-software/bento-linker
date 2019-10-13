use std::iter;
use std::cmp::Reverse;

use crate::bits::*;
use crate::errors::*;
use crate::hist::Hist;


//// Golomb-Rice code conversions
#[derive(Debug)]
pub struct GolombRice {
    k: usize,
    width: usize,
    table: Option<(Vec<u32>, Vec<u32>)>,
}

fn table_cast<U: Sym, V:Sym>(
    table: &[U]
) -> Result<Vec<V>> {
    table.iter().map(|&n| 32.cast(n)).collect()
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
        assert_eq!(decode_table.len(), 2usize.pow(width as u32));
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

    pub fn from_hist<U: Sym>(
        k: Option<usize>,
        width: usize,
        hist: &Hist<U>
    ) -> GolombRice {
        // build reverse table
        let mut decode_table: Vec<u32> = (0..2u32.pow(width as u32))
            .collect();
        decode_table.sort_by_key(|&k|
            Reverse(hist[U::try_from(k).ok().unwrap()]));
        let encode_table = reverse_table(&decode_table);

        // either use provided k, or find best k for our histogram
        let k = k.unwrap_or_else(||
           (0..=width).map(|k| {
                let gr = GolombRice::with_width(k, width);
                let size: usize = hist.iter().map(|(n, c)|
                    c * gr.encode_sym(encode_table[n.into() as usize])
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
        if let Some((encode_table, _)) = &self.table {
            n = encode_table[n as usize];
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
            n = decode_table[n as usize];
        }

        Ok((self.width.cast(n)?, diff))
    }
}


// Tests
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn encode_test() -> Result<()> {
        assert_eq!(
            GolombRice::new(8).encode_u8(0b01011100u8)?,
            bitvec![0,1,0,1,1,1,0,0]
        );
        assert_eq!(
            GolombRice::new(7).encode_u8(0b01011100u8)?,
            bitvec![0,1,0,1,1,1,0,0]
        );
        assert_eq!(
            GolombRice::new(6).encode_u8(0b01011100u8)?,
            bitvec![1,0,0,1,1,1,0,0]
        );
        assert_eq!(
            GolombRice::new(5).encode_u8(0b01011100u8)?,
            bitvec![1,1,0,1,1,1,0,0]
        );
        assert_eq!(
            GolombRice::new(4).encode_u8(0b01011100u8)?,
            bitvec![1,1,1,1,1,0,1,1,0,0]
        );
        assert_eq!(
            GolombRice::new(3).encode_u8(0b01011100u8)?,
            bitvec![1,1,1,1,1,1,1,1,1,1,1,0,1,0,0]
        );
        assert_eq!(
            GolombRice::new(2).encode_u8(0b01011100u8)?,
            bitvec![
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0
            ]
        );
        assert_eq!(
            GolombRice::new(1).encode_u8(0b01011100u8)?,
            bitvec![
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0
            ]
        );
        assert_eq!(
            GolombRice::new(0).encode_u8(0b01011100u8)?,
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
            GolombRice::new(8).decode_u8(&bitvec![0,1,0,1,1,1,0,0])?,
            (0b01011100u8, 8)
        );
        assert_eq!(
            GolombRice::new(7).decode_u8(&bitvec![0,1,0,1,1,1,0,0])?,
            (0b01011100u8, 8)
        );
        assert_eq!(
            GolombRice::new(6).decode_u8(&bitvec![1,0,0,1,1,1,0,0])?,
            (0b01011100u8, 8)
        );
        assert_eq!(
            GolombRice::new(5).decode_u8(&bitvec![1,1,0,1,1,1,0,0])?,
            (0b01011100u8, 8)
        );
        assert_eq!(
            GolombRice::new(4).decode_u8(&bitvec![1,1,1,1,1,0,1,1,0,0])?,
            (0b01011100u8, 10)
        );
        assert_eq!(
            GolombRice::new(3).decode_u8(&bitvec![
                1,1,1,1,1,1,1,1,1,1,1,0,1,0,0
            ])?,
            (0b01011100u8, 15)
        );
        assert_eq!(
            GolombRice::new(2).decode_u8(&bitvec![
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0
            ])?,
            (0b01011100u8, 23+3)
        );
        assert_eq!(
            GolombRice::new(1).decode_u8(&bitvec![
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0
            ])?,
            (0b01011100u8, 2*23+2)
        );
        assert_eq!(
            GolombRice::new(0).decode_u8(&bitvec![
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
        assert!(GolombRice::new(4)
            .decode_u8(&bitvec![1,1,1,1,1,1,1,1]).is_err());
        assert!(GolombRice::new(4)
            .decode_u8(&bitvec![1,1,1,0]).is_err());
        assert!(GolombRice::new(4)
            .decode_u8(&bitvec![]).is_err());

        Ok(())
    }

    #[test]
    fn rice_symmetry_test() -> Result<()> {
        for i in 0..8 {
            let gr = GolombRice::new(i);
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
        let mut order = [0u8; 256];
        for i in 0..256 {
            order[i] = i as u8;
        }

        let gr = GolombRice::with_table(4, 8, &order);
        assert_eq!(gr.k(), 4);

        let gr = GolombRice::from_seed(Some(4), 8,
            [0u8;100].iter().copied());
        assert_eq!(gr.k(), 4);

        let gr = GolombRice::from_seed(None, 8,
            iter::repeat(0u8).take(100));
        assert_eq!(gr.k(), 0);

        let gr = GolombRice::from_seed(None, 8,
            order.iter().copied());
        assert_eq!(gr.k(), 8);

        let gr = GolombRice::from_seed(None, 8,
            (0..=255).chain(iter::repeat(0u8).take(1000)));
        assert_eq!(gr.k(), 4);

        Ok(())
    }

    #[test]
    fn hist_symmetry_test() -> Result<()> {
        let gr = GolombRice::from_seed(
            None, 8, b"hello world!".iter().copied());
        assert_eq!(gr.k(), 1);
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

        let gr = GolombRice::from_seed(
            None, 8, b"hhhhh world!".iter().copied());
        assert_eq!(gr.k(), 1);
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

        let gr = GolombRice::from_seed(
            None, 8, b"hhhhhhhhhhh!".iter().copied());
        assert_eq!(gr.k(), 0);
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

        let gr = GolombRice::from_seed(
            None, 8, b"hhhhhhhhhhhh".iter().copied());
        assert_eq!(gr.k(), 0);
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
