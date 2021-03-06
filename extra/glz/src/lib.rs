//!
//! GLZ root
//!
//! Copyright (c) 2020, Arm Limited. All rights reserved.
//! SPDX-License-Identifier: BSD-3-Clause
//!

// utility modules
pub mod bits;
pub use bits::*;
pub mod errors;
pub use errors::*;
pub mod hist;
pub use hist::*;

// various encoding methods
pub mod leb128;
pub use leb128::*;
pub mod rice;
pub use rice::*;
pub mod glz;
pub use crate::glz::*;
