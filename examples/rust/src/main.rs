#![no_std]
mod bb;

use bb::Result;
use core::convert::TryFrom;

pub fn box1_add2(a: i32, b: i32) -> Result<u32> {
    Ok(u32::try_from(a + b).unwrap())
}

pub fn box1_hello() -> Result<()> {
    println!("Hello from rust!");
    Ok(())
}
