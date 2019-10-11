use crate::bits::*;
use crate::errors::*;


// Compressable integer storage
pub struct LEB128;

impl SymEncode for LEB128 {
    fn encode_sym<U: Sym>(
        &self,
        n: U
    ) -> Result<BitVec> {
        let mut n = n.into();
        let mut bits = BitVec::with_capacity(8);
        loop {
            if n > 0x7f {
                let x = n & 0x7f;
                n >>= 7;
                bits.push(true);
                bits.extend(7.encode_u32(x)?);
            } else {
                bits.push(false);
                bits.extend(7.encode_u32(n)?);
                break;
            }
        }

        Ok(bits)
    }

    fn decode_sym<U: Sym>(
        &self,
        bits: &BitSlice
    ) -> Result<(U, usize)> {
        let mut count = 0;
        let mut res = 0u32;
        loop {
            let byte = 8.decode_u32_at(bits, 8*count)?.0;
            res |= (byte & 0x7f).checked_shl(7*count as u32)
                .ok_or_else(|| "leb128 exceeds 32-bit limit")?;
            count += 1;

            if byte & 0x80 == 0 {
                break;
            }
        }

        Ok(((7*count).cast(res)?, 8*count))
    }
}


// Tests
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn encode_test() -> Result<()> {
        assert_eq!(
            LEB128.encode_u8(0b1001000u8)?,
            bitvec![0,1,0,0,1,0,0,0]
        );
        assert_eq!(
            LEB128.encode_u16(0b1100111001000u16)?,
            bitvec![1,1,0,0,1,0,0,0,0,0,1,1,0,0,1,1]
        );
        Ok(())
    }

    #[test]
    fn decode_test() -> Result<()> {
        assert_eq!(
            LEB128.decode_u8(&bitvec![0,1,0,0,1,0,0,0])?,
            (0b1001000u8, 8)
        );
        assert_eq!(
            LEB128.decode_u16(&bitvec![1,1,0,0,1,0,0,0,0,0,1,1,0,0,1,1])?,
            (0b1100111001000u16, 16)
        );
        Ok(())
    }

    #[test]
    fn errors_test() -> Result<()> {
        assert!(
            LEB128.decode_u8(&bitvec![1,1,0,0,1,0,0,0,0,0,1,1,0,0,1,1])
                .is_err()
        );
        Ok(())
    }
}
