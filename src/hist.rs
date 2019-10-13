use crate::bits::*;

use std::cmp::max;
use std::cmp::Reverse;
use std::marker::PhantomData;
use std::ops::Index;
use std::iter;

#[derive(Debug, Clone)]
pub struct Hist<U: Sym = u32> {
    hist: Vec<usize>,
    phantom: PhantomData<U>,
}

impl<U: Sym> Hist<U> {
    pub fn new() -> Hist<U> {
        Hist::with_capacity(0)
    }

    pub fn with_capacity(capacity: usize) -> Hist<U> {
        Hist{
            hist: Vec::with_capacity(capacity),
            phantom: PhantomData,
        }
    }

    pub fn from_seed<I: IntoIterator<Item=U>>(seed: I) -> Hist<U> {
        let mut hist = Hist::new();
        for x in seed {
            hist.increment(x);
        }
        hist
    }

    pub fn increment(&mut self, n: U) {
        self.increment_by(n, 1);
    }

    pub fn increment_by(&mut self, n: U, diff: usize) {
        let n = n.into() as usize;
        self.hist.resize(max(n+1, self.hist.len()), 0);
        self.hist[n] += diff;
    }

    pub fn decrement(&mut self, n: U) {
        self.decrement_by(n, 1);
    }

    pub fn decrement_by(&mut self, n: U, diff: usize) {
        let n = n.into() as usize;
        *self.hist.get_mut(n).unwrap_or(&mut 0) -= diff;
    }

    pub fn iter<'a>(&'a self) -> Box<Iterator<Item=(U, usize)> + 'a> {
        Box::new(self.hist.iter()
            .enumerate()
            .filter(|(_, n)| **n > 0)
            .map(|(i, n)| (U::try_from(i as u32).ok().unwrap(), *n)))
    }

    pub fn min(&self) -> Option<(U, usize)> {
        self.iter().min_by_key(|(_, n)| *n)
    }

    pub fn max(&self) -> Option<(U, usize)> {
        self.iter().max_by_key(|(_, n)| *n)
    }

    pub fn sum(&self) -> usize {
        self.iter().map(|(_, n)| n).sum()
    }
}

impl<U: Sym> Index<U> for Hist<U> {
    type Output = usize;

    fn index(&self, n: U) -> &usize {
        let n = n.into() as usize;
        self.hist.get(n).unwrap_or(&0)
    }
}

impl<U: Sym> Hist<U> {
    pub fn draw(&self, dim: Option<(usize, usize)>) {
        let dim = dim.unwrap_or((60, 10));
        let width = dim.0 - 6;
        let height = dim.1 - 1;

        let upper = self.max().unwrap().1;
        let lower = self.min().unwrap().1;
        let total = self.sum();
        let length = self.iter()
            .max_by_key(|(i, _)| (*i).into())
            .unwrap().0.into() as usize;

        let mut output = vec![vec![' '; width]; height];
        let mut sorted = self.iter().map(|(_, n)| n).collect::<Vec<_>>();
        sorted.sort_by_key(|n| Reverse(*n));
        for (x, y) in sorted.iter().enumerate() {
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
