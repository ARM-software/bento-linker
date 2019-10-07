use std::iter;
use std::convert::TryFrom;
use std::cmp::Reverse;

use super::bits::*;


//// Golomb-Rice code conversions
struct GolombRice {
    k: usize,
    width: usize,
    table: Option<(Vec<u32>, Vec<u32>)>,
}

fn table_into<U: Sym>(table: &[U]) -> Vec<u32> {
    table.iter().map(|&n| n.into()).collect()
}

fn table_from<U: Sym>(
    table: &[u32]
) -> Result<Vec<U>, <U as TryFrom<u32>>::Error> {
    table.iter().map(|&n| U::try_from(n)).collect()
}

fn table_reverse(table: &[u32]) -> Vec<u32> {
    let mut reverse_table = vec![0; table.len()];
    for (i, &n) in table.iter().enumerate() {
        reverse_table[n as usize] = i as u32;
    }
    reverse_table
}

impl GolombRice {
    #[allow(dead_code)]
    fn new(k: usize) -> GolombRice {
        GolombRice{k: k, width: 8, table: None}
    }

    #[allow(dead_code)]
    fn with_width(k: usize, width: usize) -> GolombRice {
        GolombRice{k: k, width: width, table: None}
    }

    #[allow(dead_code)]
    fn with_table<U: Sym>(k: usize, width: usize, table: &[U]) -> GolombRice {
        assert_eq!(table.len(), 2usize.pow(width as u32));
        let table = table_into(table);
        let reverse_table = table_reverse(&table);

        GolombRice{
            k: k,
            width: width,
            table: Some((
                table,
                reverse_table,
            )),
        }
    }

    #[allow(dead_code)]
    fn from_hist(
        k: Option<usize>,
        width: Option<usize>,
        hist: &[usize]
    ) -> GolombRice {
        let width = width.unwrap_or(8);
        assert_eq!(hist.len(), 2usize.pow(width as u32));

        // build reverse table
        let mut reverse_table: Vec<u32> = (
            0..2u32.pow(width as u32)).collect();
        reverse_table.sort_by_key(|&k| Reverse(hist[k as usize]));
        let table = table_reverse(&reverse_table);

        // either use provided k, or find best k for our histogram
        let k = k.unwrap_or_else(||
            (0..=8).map(|k| {
                let gr = GolombRice::with_width(k, width);
                let size: usize = hist.iter().enumerate().map(|(n, &c)|
                    c * gr.encode_sym(table[n as usize]).len()
                ).sum();
                (size, k)
            }).min().unwrap().1);

        GolombRice{
            k: k,
            width: width,
            table: Some((
                table,
                reverse_table,
            )),
        }
    }

    #[allow(dead_code)]
    fn from_seed<I, U>(
        k: Option<usize>,
        width: Option<usize>,
        seed: I
    ) -> GolombRice
    where
        I: IntoIterator<Item=U>,
        U: Sym,
    {
        let width = width.unwrap_or(8);

        // build up histogram
        let mut hist = vec![0; 2usize.pow(width as u32)];
        for x in seed {
            hist[x.into() as usize] += 1;
        }

        GolombRice::from_hist(k, Some(width), &hist)
    }

    #[allow(dead_code)]
    fn k(&self) -> usize {
        self.k
    }

    #[allow(dead_code)]
    fn width(&self) -> usize {
        self.width
    }

    #[allow(dead_code)]
    fn table<U: Sym>(&self) -> Option<Vec<U>> {
        self.table.as_ref().map(|(t, _)| table_from(t).ok().unwrap())
    }

    #[allow(dead_code)]
    fn reverse_table<U: Sym>(&self) -> Option<Vec<U>> {
        self.table.as_ref().map(|(_, t)| table_from(t).ok().unwrap())
    }
}

impl SymEncode for GolombRice {
    #[allow(dead_code)]
    fn encode_sym<U: Sym>(&self, n: U) -> BitVec {
        let mut n = n.into();
        if let Some((table, _)) = &self.table {
            n = table[n as usize];
        }

        if self.k < self.width {
            let m = 1u32 << (self.k as u32);
            let (q, r) = (n/m, n%m);
            iter::repeat(true).take(q as usize)
                .chain(iter::once(false))
                .chain(self.k.encode_sym(r))
                .collect()
        } else {
            self.width.encode_sym(n)
        }
    }

    #[allow(dead_code)]
    fn decode_sym<U: Sym>(&self,
        rice: &BitSlice
    ) -> Result<(U, usize), String> {

        let (mut n, diff) = if self.k < self.width {
            let m = 1u32 << (self.k as u32);
            let q = rice.iter().position(|b| b == false)
                .ok_or("unterminated rice code")?;
            let r = self.k.decode_u32_at(rice, q+1)?.0;
            (q as u32*m+r, q+1+self.k)
        } else {
            self.width.decode_u32(rice)?
        };

        if let Some((_, reverse_table)) = &self.table {
            n = reverse_table[n as usize];
        }

        let n = U::try_from(n).map_err(|_|
            "rice code exceeds valid width")?;
        Ok((n, diff))
    }
}


// Tests
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn encode_u8_test() {
        assert_eq!(
            GolombRice::new(8).encode_u8(0b01011100u8),
            bitvec![0,1,0,1,1,1,0,0]
        );
        assert_eq!(
            GolombRice::new(7).encode_u8(0b01011100u8),
            bitvec![0,1,0,1,1,1,0,0]
        );
        assert_eq!(
            GolombRice::new(6).encode_u8(0b01011100u8),
            bitvec![1,0,0,1,1,1,0,0]
        );
        assert_eq!(
            GolombRice::new(5).encode_u8(0b01011100u8),
            bitvec![1,1,0,1,1,1,0,0]
        );
        assert_eq!(
            GolombRice::new(4).encode_u8(0b01011100u8),
            bitvec![1,1,1,1,1,0,1,1,0,0]
        );
        assert_eq!(
            GolombRice::new(3).encode_u8(0b01011100u8),
            bitvec![1,1,1,1,1,1,1,1,1,1,1,0,1,0,0]
        );
        assert_eq!(
            GolombRice::new(2).encode_u8(0b01011100u8),
            bitvec![
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0
            ]
        );
        assert_eq!(
            GolombRice::new(1).encode_u8(0b01011100u8),
            bitvec![
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0
            ]
        );
        assert_eq!(
            GolombRice::new(0).encode_u8(0b01011100u8),
            bitvec![
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0]
        );
    }

    #[test]
    fn decode_u8_test() {
        assert_eq!(
            GolombRice::new(8).decode_u8(&bitvec![0,1,0,1,1,1,0,0]),
            Ok((0b01011100u8, 8))
        );
        assert_eq!(
            GolombRice::new(7).decode_u8(&bitvec![0,1,0,1,1,1,0,0]),
            Ok((0b01011100u8, 8))
        );
        assert_eq!(
            GolombRice::new(6).decode_u8(&bitvec![1,0,0,1,1,1,0,0]),
            Ok((0b01011100u8, 8))
        );
        assert_eq!(
            GolombRice::new(5).decode_u8(&bitvec![1,1,0,1,1,1,0,0]),
            Ok((0b01011100u8, 8))
        );
        assert_eq!(
            GolombRice::new(4).decode_u8(&bitvec![1,1,1,1,1,0,1,1,0,0]),
            Ok((0b01011100u8, 10))
        );
        assert_eq!(
            GolombRice::new(3).decode_u8(&bitvec![
                1,1,1,1,1,1,1,1,1,1,1,0,1,0,0
            ]),
            Ok((0b01011100u8, 15))
        );
        assert_eq!(
            GolombRice::new(2).decode_u8(&bitvec![
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0
            ]),
            Ok((0b01011100u8, 23+3))
        );
        assert_eq!(
            GolombRice::new(1).decode_u8(&bitvec![
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0
            ]),
            Ok((0b01011100u8, 2*23+2))
        );
        assert_eq!(
            GolombRice::new(0).decode_u8(&bitvec![
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
                1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0
            ]),
            Ok((0b01011100u8, 4*23+1))
        );
    }

    #[test]
    fn decode_u8_errors_test() {
        assert!(GolombRice::new(4)
            .decode_u8(&bitvec![1,1,1,1,1,1,1,1]).is_err());
        assert!(GolombRice::new(4)
            .decode_u8(&bitvec![1,1,1,0]).is_err());
        assert!(GolombRice::new(4)
            .decode_u8(&bitvec![]).is_err());
    }

    #[test]
    fn rice_symmetry_test() {
        for i in 0..8 {
            let gr = GolombRice::new(i);
            assert_eq!(
                gr.decode_u8(&gr.encode_u8(b'h')).map(|(n,_)| n),
                Ok(b'h')
            );
            assert_eq!(
                gr.decode(&gr.encode(b"hello world!")),
                Ok(b"hello world!".to_vec())
            );
        }
    }

    #[test]
    fn hist_k_test() {
        let mut order = [0u8; 256];
        for i in 0..256 {
            order[i] = i as u8;
        }

        let gr = GolombRice::with_table(4, 8, &order);
        assert_eq!(gr.k(), 4);

        let gr = GolombRice::from_seed(Some(4), Some(8),
            [0u8;100].iter().copied());
        assert_eq!(gr.k(), 4);

        let gr = GolombRice::from_seed(None, None,
            iter::repeat(0u8).take(100));
        assert_eq!(gr.k(), 0);

        let gr = GolombRice::from_seed(None, None,
            order.iter().copied());
        assert_eq!(gr.k(), 8);

        let gr = GolombRice::from_seed(None, None,
            (0..=255).chain(iter::repeat(0u8).take(1000)));
        assert_eq!(gr.k(), 4);
    }

    #[test]
    fn hist_symmetry_test() {
        let gr = GolombRice::from_seed(
            None, None, b"hello world!".iter().copied());
        assert_eq!(gr.k(), 1);
        assert_eq!(
            gr.encode_u8(b'h'),
            bitvec![1,1,1,0,0]
        );
        assert_eq!(
            gr.decode_u8(&gr.encode_u8(b'h')), 
            Ok((b'h', 5))
        );
        assert_eq!(
            gr.encode(b"hello world!").len(),
            40
        );
        assert_eq!(
            gr.decode(&gr.encode(b"hello world!")),
            Ok(b"hello world!".to_vec())
        );

        let gr = GolombRice::from_seed(
            None, None, b"hhhhh world!".iter().copied());
        assert_eq!(gr.k(), 1);
        assert_eq!(
            gr.encode_u8(b'h'),
            bitvec![0,0]
        );
        assert_eq!(
            gr.decode_u8(&gr.encode_u8(b'h')), 
            Ok((b'h', 2))
        );
        assert_eq!(
            gr.encode(b"hhhhh world!").len(),
            36
        );
        assert_eq!(
            gr.decode(&gr.encode(b"hhhhh world!")),
            Ok(b"hhhhh world!".to_vec())
        );

        let gr = GolombRice::from_seed(
            None, None, b"hhhhhhhhhhh!".iter().copied());
        assert_eq!(gr.k(), 0);
        assert_eq!(
            gr.encode_u8(b'h'),
            bitvec![0]
        );
        assert_eq!(
            gr.decode_u8(&gr.encode_u8(b'h')), 
            Ok((b'h', 1))
        );
        assert_eq!(
            gr.encode(b"hhhhhhhhhhh!").len(),
            13
        );
        assert_eq!(
            gr.decode(&gr.encode(b"hhhhhhhhhhh!")),
            Ok(b"hhhhhhhhhhh!".to_vec())
        );

        let gr = GolombRice::from_seed(
            None, None, b"hhhhhhhhhhhh".iter().copied());
        assert_eq!(gr.k(), 0);
        assert_eq!(
            gr.encode_u8(b'h'),
            bitvec![0]
        );
        assert_eq!(
            gr.decode_u8(&gr.encode_u8(b'h')), 
            Ok((b'h', 1))
        );
        assert_eq!(
            gr.encode(b"hhhhhhhhhhhh").len(),
            12
        );
        assert_eq!(
            gr.decode(&gr.encode(b"hhhhhhhhhhhh")),
            Ok(b"hhhhhhhhhhhh".to_vec())
        );
    }
}
