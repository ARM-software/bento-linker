#![no_std]
use bb::*;
use core::convert::TryFrom;

#[export(export::boxrust_add2)]
pub fn add2(a: i32, b: i32) -> Result<u32> {
    Ok(u32::try_from(a + b).unwrap())
}

#[export(export::boxrust_hello)]
pub fn hello() -> Result<()> {
    println!("Hello from Rust!");
    Ok(())
}

// fib example
static mut FIB_BUFFER: [u8; 64] = [0; 64];

#[export(export::boxrust_fib_alloc)]
pub fn fib_alloc(size: usize) -> Option<&'static mut u8> {
    let buffer = unsafe { &mut FIB_BUFFER };
    if size > buffer.len() {
        return None;
    }

    Some(&mut buffer[0])
}

#[export(export::boxrust_fib_next)]
pub fn fib_next(next: &mut u32, a: u32, b: u32) -> Result<()> {
    *next = a + b;
    Ok(())
}

#[export(export::boxrust_fib)]
pub fn fib(buffer: &mut [u32], a: u32, b: u32) -> Result<()> {
    if buffer.len() < 2 {
        Err(Error::Inval)?;
    }

    buffer[0] = a;
    buffer[1] = b;
    for i in 2..buffer.len() {
        buffer[i] = buffer[i-1] + buffer[i-2];
    }

    Ok(())
}

// quicksort example
static mut QSORT_BUFFER: [u8; 64] = [0; 64];

#[export(export::boxrust_qsort_alloc)]
pub fn qsort_alloc(size: usize) -> Option<&'static mut u8> {
    let buffer = unsafe { &mut QSORT_BUFFER };
    if size > buffer.len() {
        return None;
    }

    Some(&mut buffer[0])
}

#[export(export::boxrust_qsort_partition)]
pub fn qsort_partition(buffer: &mut [u32], pivot: u32) -> Result<usize> {
    let mut i = 0;
    for j in 0..buffer.len() {
        if buffer[j] < pivot {
            buffer.swap(i, j);
            i += 1;
        }
    }

    Ok(i)
}

#[export(export::boxrust_qsort)]
pub fn qsort(buffer: &mut [u32]) -> Result<()> {
    if buffer.len() == 0 {
        return Ok(());
    }

    let pivot_i = buffer.len()-1;
    let pivot = buffer[pivot_i];
    let i = qsort_partition(&mut buffer[..pivot_i], pivot)?;
    buffer.swap(i, pivot_i);

    qsort(&mut buffer[..i])?;
    qsort(&mut buffer[i+1..])?;
    Ok(())
}

