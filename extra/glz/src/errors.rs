//!
//! GLZ error handling
//!
//! Copyright (c) 2020, Arm Limited. All rights reserved.
//! SPDX-License-Identifier: BSD-3-Clause
//!

use error_chain::error_chain;
use std::convert::TryFrom;



error_chain! {
    foreign_links {
        Utf8(::std::string::FromUtf8Error);
        IO(::std::io::Error);
        TryFromInt(::std::num::TryFromIntError);
        Infallible(::std::convert::Infallible);
    }

    errors {}
}


// This is a hack to get around the craziness that is trying to get
// a <U:Sym as TryFrom<u32>>::Error into our error_chain Error.
// I have no idea how to do this or even if it's possible??
// Anyways just use cast instead of try_from.
pub trait CastNonsense<U>: Sized {
    fn cast_nonsense(n: U) -> Result<Self>;
}

impl<U, V> CastNonsense<U> for V
where
    V: TryFrom<U>,
    Error: From<<V as TryFrom<U>>::Error>,
{
    fn cast_nonsense(n: U) -> Result<Self> {
        Ok(V::try_from(n)?)
    }
}
