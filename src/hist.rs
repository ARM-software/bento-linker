use crate::bits::*;
use crate::errors::*;

use std::cmp::max;
use std::cmp::Reverse;
use std::ops::Index;
use std::iter;
use std::fmt;
use std::fmt::Debug;


// Simple histogram class for Sym types
#[derive(Clone)]
pub struct Hist {
    hist: Vec<usize>,
    table: Option<(Vec<u32>, Vec<u32>)>,
    //bound: Option<usize>,
}

impl Hist {
    pub fn new() -> Self {
        Self::with_capacity(0)
    }

    pub fn with_table<U: Sym>(decode_table: &[U]) -> Self {
        // convert to u32s
        let decode_table: Vec<u32> = decode_table.iter()
            .map(|n| (*n).into())
            .collect();

        // invert for encode table
        let mut encode_table = vec![0; decode_table.len()];
        for (i, &n) in decode_table.iter().enumerate() {
            encode_table[n as usize] = i as u32;
        }

        Self{
            hist: Vec::with_capacity(decode_table.len()),
            table: Some((encode_table, decode_table)),
        }
    }

    pub fn with_capacity(capacity: usize) -> Self {
        Self{
            hist: Vec::with_capacity(capacity),
            table: None,
        }
    }

    pub fn from_seed<I: IntoIterator<Item=U>, U: Sym>(seed: I) -> Self {
        let mut hist = Self::new();
        for x in seed {
            hist.increment(x);
        }
        hist
    }

    pub fn bound(&self) -> usize {
        match &self.table {
            Some((_, table)) => table.len(),
            None => self.upper::<u32>()
                .map(|(i, _)| i + 1)
                .unwrap_or(0) as usize,
        }
    }

    pub fn get<U: Sym>(&self, n: U) -> usize {
        self[n]
    }

    pub fn get_bounded<U: Sym>(&self, n: U, bound: usize) -> usize {
        let mut count = 0;
        let mut i = self.map_decode(n).unwrap().into() as usize;
        while i < self.hist.len() {
            count += self.hist[i];
            i += bound
        }
        count
    }

    pub fn increment<U: Sym>(&mut self, n: U) {
        self.increment_by(n, 1);
    }

    pub fn increment_by<U: Sym>(&mut self, n: U, diff: usize) {
        let n = self.map_decode(n).unwrap().into() as usize;
        self.hist.resize(max(n+1, self.hist.len()), 0);
        self.hist[n] += diff;
    }

    pub fn decrement<U: Sym>(&mut self, n: U) {
        self.decrement_by(n, 1);
    }

    pub fn decrement_by<U: Sym>(&mut self, n: U, diff: usize) {
        let n = self.map_decode(n).unwrap().into() as usize;
        *self.hist.get_mut(n).unwrap_or(&mut 0) -= diff;
    }

    pub fn iter<'a, U: Sym>(&'a self) -> Box<Iterator<Item=(U, usize)> + 'a> {
        Box::new(self.hist.iter()
            .enumerate()
            .filter(|(_, n)| **n > 0)
            .map(move |(i, n)| {
                let i = U::cast(self.map_encode(i as u32).unwrap()).unwrap();
                (i, *n)
            }))
    }

    pub fn iter_bounded<'a, U: Sym>(
        &'a self,
        bound: usize,
    ) -> Box<Iterator<Item=(U, usize)> + 'a> {
        Box::new((0..bound)
            .map(|i| U::cast(i as u32).unwrap())
            .map(move |i| (i, self.get_bounded(i, bound)))
            .filter(|(_, n)| *n > 0))
    }

    pub fn min<U: Sym>(&self) -> Option<(U, usize)> {
        self.iter().min_by_key(|(_, n)| *n)
    }

    pub fn min_bounded<U: Sym>(&self, bound: usize) -> Option<(U, usize)> {
        self.iter_bounded(bound).min_by_key(|(_, n)| *n)
    }

    pub fn max<U: Sym>(&self) -> Option<(U, usize)> {
        self.iter().max_by_key(|(_, n)| *n)
    }

    pub fn max_bounded<U: Sym>(&self, bound: usize) -> Option<(U, usize)> {
        self.iter_bounded(bound).max_by_key(|(_, n)| *n)
    }

    pub fn lower<U: Sym>(&self) -> Option<(U, usize)> {
        self.iter().min_by_key(|(i, _)| *i)
    }

    pub fn lower_bounded<U: Sym>(&self, bound: usize) -> Option<(U, usize)> {
        self.iter_bounded(bound).min_by_key(|(i, _)| *i)
    }

    pub fn upper<U: Sym>(&self) -> Option<(U, usize)> {
        self.iter().max_by_key(|(i, _)| *i)
    }

    pub fn upper_bounded<U: Sym>(&self, bound: usize) -> Option<(U, usize)> {
        self.iter_bounded(bound).max_by_key(|(i, _)| *i)
    }

    pub fn sum(&self) -> usize {
        self.iter::<u32>().map(|(_, n)| n).sum()
    }

    pub fn encode_table<U: Sym>(&self) -> Result<Vec<U>> {
        //self.prep_table().0.iter().map(|&n| U::cast(n)).collect()
        match &self.table {
            Some((table, _)) => table.iter().map(|&n| U::cast(n)).collect(),
            None             => Ok(vec![]),
        }
    }

    pub fn decode_table<U: Sym>(&self) -> Result<Vec<U>> {
        match &self.table {
            Some((_, table)) => table.iter().map(|&n| U::cast(n)).collect(),
            None             => Ok(vec![]),
        }
    }

    pub fn sort(&mut self) {
        self.table = None;
        self.sort_bounded(self.bound());
    }

    pub fn sort_bounded(&mut self, bound: usize) {
        self.table = None;

        // sort histogram keys by reversed frequency
        let mut decode_table: Vec<u32> = (0..bound as u32).collect();
        decode_table.sort_by_key(|&k| Reverse(self.get_bounded(k, bound)));

        // invert for encode table
        let mut encode_table = vec![0; decode_table.len()];
        for (i, &n) in decode_table.iter().enumerate() {
            encode_table[n as usize] = i as u32;
        }

        self.table = Some((encode_table, decode_table));
    }
}

impl<U: Sym> Index<U> for Hist {
    type Output = usize;

    fn index(&self, n: U) -> &usize {
        let n = self.map_decode(n).unwrap().into() as usize;
        self.hist.get(n).unwrap_or(&0)
    }
}

impl Debug for Hist {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let mut entries = self.iter::<u32>().collect::<Vec<_>>();
        entries.sort();
        write!(f, "Hist{{{:?}}}", entries)
    }
}

impl Hist {
    pub fn draw(&self, dim: Option<(usize, usize)>) {
        let dim = dim.unwrap_or((60, 10));
        let width = dim.0 - 6;
        let height = dim.1 - 1;

        let upper = self.max::<u32>().unwrap().1;
        let lower = self.min::<u32>().unwrap().1;
        let total = self.sum();
        let length = self.bound();

        let mut output = vec![vec![' '; width]; height];
        for (x, y) in self.iter::<u32>().map(|(x, y)| (x as usize, y)) {
            let x = (width-1) * x / (length-1);
            let y = (height-1) * (y-lower) / (upper-lower);
            output[height-1-y][x] = '.'
        }

        for i in 0..output.len() {
            if i == 0 {
                print!(" {:2}%", 100*upper/total);
            } else {
                print!("    ");
            }

            println!(" |{}", output[i].iter().collect::<String>());
        }

        println!(" {:2}% +{}",
            100*lower/total,
            iter::repeat('-').take(width).collect::<String>());
    }
}

// Bijective mapping for encoding schemes
// useful for shifting the probabilities of symbols around
pub trait Biject {
    fn map_encode<U: Sym>(&self, n: U) -> Result<U>;
    fn map_decode<U: Sym>(&self, n: U) -> Result<U>;
}

impl Biject for Hist {
    fn map_encode<U: Sym>(&self, n: U) -> Result<U> {
        if let Some((table, _)) = &self.table {
            let n = u32::cast(n)?;
            let (m, n) = (n - n % table.len() as u32, n % table.len() as u32);
            let n = table.get(n as usize).unwrap_or(&n);
            U::cast(m + n)
        } else {
            Ok(n)
        }
    }

    fn map_decode<U: Sym>(&self, n: U) -> Result<U> {
        if let Some((_, table)) = &self.table {
            let n = u32::cast(n)?;
            let (m, n) = (n - n % table.len() as u32, n % table.len() as u32);
            let n = table.get(n as usize).unwrap_or(&n);
            U::cast(m + n)
        } else {
            Ok(n)
        }
    }
}

#[derive(Debug, Clone)]
pub struct BijectEncoder<E: SymEncode, B: Biject> {
    encoder: E,
    bijecter: B,
}

impl<E: SymEncode, B: Biject> BijectEncoder<E, B> {
    pub fn new(encoder: E, bijecter: B) -> Self{
        Self{encoder, bijecter}
    }

    pub fn encoder(&self) -> &E {
        &self.encoder
    }

    pub fn encoder_mut(&mut self) -> &mut E {
        &mut self.encoder
    }

    pub fn bijecter(&self) -> &B {
        &self.bijecter
    }

    pub fn bijecter_mut(&mut self) -> &mut B {
        &mut self.bijecter
    }
}

impl<E: SymEncode, B: Biject> SymEncode for BijectEncoder<E, B> {
    fn encode_sym<U: Sym>(&self, n: U) -> Result<BitVec> {
        self.encoder.encode_sym(self.bijecter.map_encode(n)?)
    }

    fn decode_sym<U: Sym>(&self, bits: &BitSlice) -> Result<(U, usize)> {
        let (n, diff) = self.encoder.decode_sym(bits)?;
        Ok((self.bijecter.map_decode(n)?, diff))
    }
}


// some tests
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn simple_hist_test() {
        let mut hist = Hist::new();
        for i in 0..100u32 {
            hist.increment(i);
        }
        assert_eq!(hist[0u32], 1);
        assert_eq!(hist[99u32], 1);
        assert_eq!(hist.lower(), Some((0u32, 1)));
        assert_eq!(hist.upper(), Some((99u32, 1)));
        assert_eq!(hist.sum(), 100);

        let mut hist = Hist::new();
        for i in 0..100u32 {
            hist.increment_by(i, i as usize);
        }
        assert_eq!(hist[0u32], 0);
        assert_eq!(hist[99u32], 99);
        assert_eq!(hist.min(), Some((1u32, 1)));
        assert_eq!(hist.max(), Some((99u32, 99)));
        assert_eq!(hist.lower(), Some((1u32, 1)));
        assert_eq!(hist.upper(), Some((99u32, 99)));
        assert_eq!(hist.sum(), 99*100/2);

        let mut hist = Hist::new();
        for _ in 0..100u32 {
            hist.increment(99u32);
        }
        assert_eq!(hist[0u32], 0);
        assert_eq!(hist[99u32], 100);
        assert_eq!(hist.min(), Some((99u32, 100)));
        assert_eq!(hist.max(), Some((99u32, 100)));
        assert_eq!(hist.lower(), Some((99u32, 100)));
        assert_eq!(hist.upper(), Some((99u32, 100)));
        assert_eq!(hist.sum(), 100);
    }

    #[test]
    fn bounded_hist_test() {
        let mut hist = Hist::new();
        for i in 0..100u32 {
            hist.increment(i);
        }
        assert_eq!(hist[0u32], 1);
        assert_eq!(hist[99u32], 1);
        assert_eq!(hist.get_bounded(0u32, 50), 2);
        assert_eq!(hist.get_bounded(49u32, 50), 2);
        assert_eq!(hist.lower(), Some((0u32, 1)));
        assert_eq!(hist.upper(), Some((99u32, 1)));
        assert_eq!(hist.lower_bounded(50), Some((0u32, 2)));
        assert_eq!(hist.upper_bounded(50), Some((49u32, 2)));
        assert_eq!(hist.sum(), 100);

        let mut hist = Hist::new();
        for i in 0..100u32 {
            hist.increment_by(i, i as usize);
        }
        assert_eq!(hist[0u32], 0);
        assert_eq!(hist[99u32], 99);
        assert_eq!(hist.get_bounded(0u32, 50), 0+50);
        assert_eq!(hist.get_bounded(49u32, 50), 49+99);
        assert_eq!(hist.min(), Some((1u32, 1)));
        assert_eq!(hist.max(), Some((99u32, 99)));
        assert_eq!(hist.min_bounded(50), Some((0u32, 0+50)));
        assert_eq!(hist.max_bounded(50), Some((49u32, 49+99)));
        assert_eq!(hist.lower(), Some((1u32, 1)));
        assert_eq!(hist.upper(), Some((99u32, 99)));
        assert_eq!(hist.lower_bounded(50), Some((0u32, 0+50)));
        assert_eq!(hist.upper_bounded(50), Some((49u32, 49+99)));
        assert_eq!(hist.sum(), 99*100/2);

        let mut hist = Hist::new();
        for _ in 0..100u32 {
            hist.increment(99u32);
        }
        assert_eq!(hist[0u32], 0);
        assert_eq!(hist[99u32], 100);
        assert_eq!(hist.get_bounded(0u32, 50), 0);
        assert_eq!(hist.get_bounded(49u32, 50), 100);
        assert_eq!(hist.min(), Some((99u32, 100)));
        assert_eq!(hist.max(), Some((99u32, 100)));
        assert_eq!(hist.min_bounded(50), Some((49u32, 100)));
        assert_eq!(hist.max_bounded(50), Some((49u32, 100)));
        assert_eq!(hist.lower(), Some((99u32, 100)));
        assert_eq!(hist.upper(), Some((99u32, 100)));
        assert_eq!(hist.lower_bounded(50), Some((49u32, 100)));
        assert_eq!(hist.upper_bounded(50), Some((49u32, 100)));
        assert_eq!(hist.sum(), 100);
    }

    #[test]
    fn sorted_hist_test() {
        let mut hist = Hist::new();
        for i in 0..100u32 {
            hist.increment(i);
        }
        hist.sort();
        assert_eq!(hist[0u32], 1);
        assert_eq!(hist[99u32], 1);
        assert_eq!(hist.lower(), Some((0u32, 1)));
        assert_eq!(hist.upper(), Some((99u32, 1)));
        assert_eq!(hist.sum(), 100);

        let mut hist = Hist::new();
        for i in 0..100u32 {
            hist.increment_by(i, i as usize);
        }
        hist.sort();
        assert_eq!(hist[0u32], 99);
        assert_eq!(hist[99u32], 0);
        assert_eq!(hist.min(), Some((98u32, 1)));
        assert_eq!(hist.max(), Some((0u32, 99)));
        assert_eq!(hist.lower(), Some((0u32, 99)));
        assert_eq!(hist.upper(), Some((98u32, 1)));
        assert_eq!(hist.sum(), 99*100/2);

        let mut hist = Hist::new();
        for _ in 0..100u32 {
            hist.increment(99u32);
        }
        hist.sort();
        assert_eq!(hist[0u32], 100);
        assert_eq!(hist[99u32], 0);
        assert_eq!(hist.min(), Some((0u32, 100)));
        assert_eq!(hist.max(), Some((0u32, 100)));
        assert_eq!(hist.lower(), Some((0u32, 100)));
        assert_eq!(hist.upper(), Some((0u32, 100)));
        assert_eq!(hist.sum(), 100);
    }

    #[test]
    fn sort_bounded_hist_test() {
        let mut hist = Hist::new();
        for i in 0..100u32 {
            hist.increment(i);
        }
        hist.sort_bounded(50);
        assert_eq!(hist[0u32], 1);
        assert_eq!(hist[99u32], 1);
        assert_eq!(hist.get_bounded(0u32, 50), 2);
        assert_eq!(hist.get_bounded(49u32, 50), 2);
        assert_eq!(hist.lower(), Some((0u32, 1)));
        assert_eq!(hist.upper(), Some((99u32, 1)));
        assert_eq!(hist.lower_bounded(50), Some((0u32, 2)));
        assert_eq!(hist.upper_bounded(50), Some((49u32, 2)));
        assert_eq!(hist.sum(), 100);

        let mut hist = Hist::new();
        for i in 0..100u32 {
            hist.increment_by(i, i as usize);
        }
        hist.sort_bounded(50);
        assert_eq!(hist[0u32], 49);
        assert_eq!(hist[99u32], 50);
        assert_eq!(hist.get_bounded(0u32, 50), 49+99);
        assert_eq!(hist.get_bounded(49u32, 50), 0+50);
        assert_eq!(hist.min(), Some((48u32, 1)));
        assert_eq!(hist.max(), Some((50u32, 99)));
        assert_eq!(hist.min_bounded(50), Some((49u32, 0+50)));
        assert_eq!(hist.max_bounded(50), Some((0u32, 49+99)));
        assert_eq!(hist.lower(), Some((0u32, 49)));
        assert_eq!(hist.upper(), Some((99u32, 50)));
        assert_eq!(hist.lower_bounded(50), Some((0u32, 49+99)));
        assert_eq!(hist.upper_bounded(50), Some((49u32, 0+50)));
        assert_eq!(hist.sum(), 99*100/2);

        let mut hist = Hist::new();
        for _ in 0..100u32 {
            hist.increment(99u32);
        }
        hist.sort_bounded(50);
        assert_eq!(hist[0u32], 0);
        assert_eq!(hist[99u32], 0);
        assert_eq!(hist[50u32], 100);
        assert_eq!(hist.get_bounded(0u32, 50), 100);
        assert_eq!(hist.get_bounded(49u32, 50), 0);
        assert_eq!(hist.min(), Some((50u32, 100)));
        assert_eq!(hist.max(), Some((50u32, 100)));
        assert_eq!(hist.min_bounded(50), Some((0u32, 100)));
        assert_eq!(hist.max_bounded(50), Some((0u32, 100)));
        assert_eq!(hist.lower(), Some((50u32, 100)));
        assert_eq!(hist.upper(), Some((50u32, 100)));
        assert_eq!(hist.lower_bounded(50), Some((0u32, 100)));
        assert_eq!(hist.upper_bounded(50), Some((0u32, 100)));
        assert_eq!(hist.sum(), 100);
    }
}
