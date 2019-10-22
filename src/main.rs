use glz::bits::*;
use glz::errors::*;
use glz::LEB128;
use glz::GLZ;
use glz::Hist;

use std::io;
use std::fs;
use std::io::Write;
use std::io::Read;
use std::fs::File;
use std::path::PathBuf;
use std::time::Instant;
use std::thread;
use std::cmp::min;
use std::collections::HashMap;
use std::process;

use num_derive::FromPrimitive;    
use num_traits::FromPrimitive;
use error_chain::bail;

use structopt::StructOpt;
use indicatif::ProgressBar;
use indicatif::ProgressStyle;
use indicatif::MultiProgress;
use indicatif::HumanBytes;
use indicatif::HumanDuration;

const MAGIC: &[u8] = b"\0glz\x01\0\0\0";

#[derive(Debug, PartialEq, Eq, Hash, FromPrimitive, Clone, Copy)]
enum Field {
    K = 2,
    TABLE = 3,
    L = 4,
    M = 5,
    NAMES = 1,
    BLOB = 0,
}

#[derive(Debug, StructOpt)]
#[structopt(rename_all = "kebab")]
struct CommonOpt {
    /// Override K-constant, this is the width of the Golomb-Rice code's
    /// denominator in bits. By default the best K is approximated from
    /// the input data.
    #[structopt(short = "K")]
    k: Option<usize>,

    /// Override Golomb-Rice table. By default the best table is approximated
    /// from the input data.
    #[structopt(long)]
    table: Vec<u32>,

    /// Number of passes to use when finding optimal Golomb-Rice table
    #[structopt(long, default_value = "1")]
    passes: u32,

    /// Width of reference length in bits.
    #[structopt(short = "L", default_value = "5")]
    l: usize,

    /// Width of reference offset chunks in bits.
    #[structopt(short = "M", default_value = "4")]
    m: usize,

    /// Limit CLI noise
    #[structopt(short, long)]
    quiet: bool,

    /// Print full Golomb Rice table, can be useful with --no_headers.
    #[structopt(short, long)]
    print_table: bool,

    /// Don't use headers in compressed files. This requires that both
    /// -K and --table be provided when decompressing.
    #[structopt(long)]
    no_headers: bool,
}

#[derive(Debug, StructOpt)]
#[structopt(rename_all = "kebab")]
struct EncodeOpt {
    /// Set of files
    #[structopt(parse(from_os_str))]
    input: Vec<PathBuf>,

    /// Output file
    #[structopt(short, long)]
    output: Option<String>,

    #[structopt(flatten)]
    common: CommonOpt,
}

#[derive(Debug, StructOpt)]
#[structopt(rename_all = "kebab")]
struct DecodeOpt {
    /// Input file
    #[structopt(parse(from_os_str))]
    input: PathBuf,

    /// File to decompress. This is only available when
    /// headers are included.
    #[structopt(short, long)]
    file: Option<String>,

    /// Offset to start decompression
    #[structopt(long)]
    off: Option<usize>,

    /// Number of bytes to decompress
    #[structopt(long)]
    len: Option<usize>,

    /// Output file
    #[structopt(short, long)]
    output: Option<String>,

    #[structopt(flatten)]
    common: CommonOpt,
}

#[derive(Debug, StructOpt)]
#[structopt(rename_all = "kebab")]
struct LsOpt {
    /// Input file
    #[structopt(parse(from_os_str))]
    input: PathBuf,

    #[structopt(flatten)]
    common: CommonOpt,
}

#[derive(Debug, StructOpt)]
#[structopt(
    name = "glz",
    rename_all = "kebab",
    about = "compressor and decompressor for GLZ over Rice, \
        a granular compression algorithm"
)]
enum Opt {
    /// Compress a set of files with GLZ
    Encode {
        #[structopt(flatten)]
        encode: EncodeOpt,
    },

    /// Decompress a file with GLZ
    Decode {
        #[structopt(flatten)]
        decode: DecodeOpt,
    },

    /// List files in a compressed file
    Ls {
        #[structopt(flatten)]
        ls: LsOpt,
    },
}


// Double progress bar (maybe single)
fn with_prog_all<F, R>(
    msg: &str,
    quiet: bool,
    paths: &[PathBuf],
    inputs: &[usize],
    f: F,
) -> Result<R>
where
    F: for<'a> FnOnce((
        Box<FnMut(usize)+'a>,
        Box<FnMut(usize)+'a>,
    )) -> Result<R>,
{
    if quiet {
        return f((Box::new(|_|()), Box::new(|_|())))
    }

    let mprog = MultiProgress::new();
    let prog1 = mprog.add(ProgressBar::hidden());
    prog1.set_style(ProgressStyle::default_bar()
        .template("{msg:<20} [{wide_bar}] {bytes:>8}/{total_bytes:8}")
        .progress_chars("##-"));
    prog1.set_message(msg);
    prog1.set_length(inputs.iter().sum::<usize>() as u64);
    if inputs.len() > 1 {
        let prog2 = mprog.add(ProgressBar::hidden());
        prog2.set_style(ProgressStyle::default_bar()
            .template("{msg:<20} [{wide_bar}] {bytes:>8}/{total_bytes:8}")
            .progress_chars("##-"));
        let prog2_reset = |i: usize| {
            let i = inputs.len()-1-i;
            let path = paths[i].to_string_lossy();
            prog2.set_message(&path[path.len()-min(msg.len(), path.len())..]);
            prog2.set_length(inputs[i] as u64);
            prog2.reset();
        };
        prog2_reset(0);
        let mprog = thread::spawn(move || mprog.join().unwrap());

        let mut i = 0;
        let r = f((
            Box::new(|diff| {
                i += diff;
                prog1.inc(prog2.position());
                if i < inputs.len() {
                    prog2_reset(i);
                }
            }),
            Box::new(|diff| {
                prog2.inc(diff as u64);
            })
        ));

        if r.is_ok() {
            prog1.finish();
            prog2.finish();
            mprog.join().unwrap();
        }

        r
    } else {
        let mprog = thread::spawn(move || mprog.join().unwrap());

        let r = f((
            Box::new(|_| ()),
            Box::new(|diff| {
                prog1.inc(diff as u64);
            })
        ));

        if r.is_ok() {
            prog1.finish();
            mprog.join().unwrap();
        }

        r
    }
}

// Single progress bar
fn with_prog<F, R>(
    msg: &str,
    quiet: bool,
    inputs: usize,
    f: F,
) -> Result<R>
where
    F: for<'a> FnOnce(
        Box<FnMut(usize)+'a>,
    ) -> Result<R>,
{
    with_prog_all(msg, quiet, &[], &[inputs], |(_, prog)| f(prog))
}

// field reader/writers
trait FieldWrite {
    fn write_field(
        &mut self,
        field: Field,
        bits: &BitSlice,
    ) -> Result<()>;
}

impl<T: Write> FieldWrite for T {
    fn write_field(
        &mut self,
        field: Field,
        bits: &BitSlice
    ) -> Result<()> {
        let res: Result<_> = (|| {
            let mut bits = BitVec::from(bits);
            bits.resize(((bits.len()+8-1)/8)*8, false);
            let bytes = 8usize.decode::<u8>(&bits)?;

            self.write_all(&[field as u8])?;
            self.write_all(&8usize.decode::<u8>(
                &LEB128.encode_u32(bytes.len() as u32)?
            )?)?;
            self.write_all(&bytes)?;
            Ok(())
        })();
        res.chain_err(|| format!("could not write field {:?}", field))
    }
}

trait FieldRead {
    fn read_fields<'a>(
        &mut self,
        buf: &'a mut Vec<u8>,
    ) -> Result<HashMap<Field, &'a BitSlice>>;
}

impl<T: Read> FieldRead for T {
    fn read_fields<'a>(
        &mut self,
        buf: &'a mut Vec<u8>,
    ) -> Result<HashMap<Field, &'a BitSlice>> {
        let res: Result<_> = (|buf: &'a mut _| {
            let mut fields: HashMap<Field, &BitSlice> = HashMap::new();

            self.read_to_end(buf)?;
            let bits: &BitSlice = buf.as_bitslice();

            let mut off = 0;
            while off < bits.len() {
                let (field, diff) = LEB128.decode_u32_at(bits, off)?;
                off += diff;
                let (len, diff) = LEB128.decode_u32_at(bits, off)?;
                let len = len as usize;
                off += diff;

                if let Some(field) = Field::from_u32(field) {
                    if off+8*len > bits.len() {
                        bail!("found truncated field {:?}", field);
                    }
                    fields.insert(field, &bits[off..off+8*len]);
                } else {
                    println!("unknown field 0x{:x}", field);
                }
                off += 8*len;
            }

            Ok(fields)
        })(buf);
        res.chain_err(|| "could not read fields")
    }
}

fn encode(opt: &EncodeOpt) -> Result<()> {
    // time ourselves
    let time = Instant::now();

    // read all files into buffers
    let paths: &[PathBuf] = &opt.input;
    let inputs: Vec<Vec<u8>> = paths.iter()
        .map(|path| fs::read(path))
        .collect::<io::Result<_>>()?;
    let inputs: Vec<&[u8]> = inputs.iter()
        .map(|data| data.as_slice())
        .collect();

    // get relevant options and defaults
    let l = opt.common.l;
    let m = opt.common.m;

    // estimate k/table if necessary
    let glz = match (opt.common.k, &opt.common.table) {
        (k, table) if table.len() == 0 => {
            let mut hist = Hist::new();
            for _ in 0..opt.common.passes {
                let (glz, bits) = with_prog_all(
                    "finding constants...",
                    opt.common.quiet,
                    &paths,
                    &inputs.iter().map(|x| x.len()).collect::<Vec<_>>(),
                    |prog| {
                        let glz = GLZ::with_config(GLZ::DEFAULT_K, l, m);
                        let (bits, _) = glz.encode_all_with_prog(
                            &inputs, prog)?;
                        Ok((glz, bits))
                    }
                )?;
                hist = with_prog(
                    "optimizing...",
                    opt.common.quiet,
                    bits.len() / (GLZ::WIDTH+1),
                    |prog| {
                        let mut hist = Hist::new();
                        glz.traverse_syms_with_prog(&bits, |op: u32| {
                            hist.increment(op);
                        }, prog)?;
                        Ok(hist)
                    }
                )?;
            }

            if !opt.common.quiet {
                let mut hist = hist.clone();
                hist.sort();
                hist.draw(None);
            }

            GLZ::from_hist(k, l, m, &hist)
        },
        (Some(k), table) => {
            GLZ::with_table(k, l, m, table)
        },
        _ => {
            bail!("can't solve for just K, please provide --table");
        }
    };

    let k = glz.k();
    let table = glz.decode_table::<u32>()?;

    let bound = 2usize.pow(GLZ::WIDTH as u32)
        + 2usize.pow(l as u32)
        + 2usize.pow(m as u32);
    if table.len() != bound {
        bail!("table is incorrect size, found {}, expected {}",
            table.len(), bound);
    }

    println!("K = {}", k);
    if l != GLZ::DEFAULT_L {
        println!("L = {}", l);
    }
    if m != GLZ::DEFAULT_M {
        println!("M = {}", m);
    }
    print!("table = [");
    if opt.common.print_table {
        println!();
        for i in (0..table.len()).step_by(8) {
            print!("    ");
            for j in 0..8 {
                if let Some(x) = table.get(i+j) {
                    print!("0x{:03x}, ", x);
                } else {
                    break;
                }
            }
            println!();
        }
    } else {
        print!("0x{:03x}, 0x{:03x}, 0x{:03x} ... \
                0x{:03x}, 0x{:03x}, 0x{:03x}",
            table[0],
            table[1],
            table[2],
            table[table.len()-3],
            table[table.len()-2],
            table[table.len()-1]
        );
    }
    println!("]");

    let (output, ranges) = with_prog_all(
        "compressing...",
        opt.common.quiet,
        &paths,
        &inputs.iter().map(|x| x.len()).collect::<Vec<_>>(),
        |prog| {
            glz.encode_all_with_prog(&inputs, prog)
        }
    )?;

    if let Some(ref outfile) = opt.output {
        let mut f = File::create(outfile)?;
        if !opt.common.no_headers {
            f.write_all(&MAGIC)?;
            f.write_field(Field::NAMES,
                &paths.iter().zip(ranges).map(|(path, (off, len))| {
                        let path = path.to_string_lossy();
                        let path = path.as_bytes();
                        Ok(
                            LEB128.encode_u32(path.len() as u32)?.iter()
                                .chain(8.encode::<u8>(path)?)
                                .chain(LEB128.encode_u32(off as u32)?)
                                .chain(LEB128.encode_u32(len as u32)?)
                                .collect::<BitVec>()
                        )
                    })
                    .collect::<Result<Vec<_>>>()?
                    .iter().flatten().collect::<BitVec>()
            )?;
            f.write_field(Field::K,
                &LEB128.encode_u32(k as u32)?
            )?;
            if l != GLZ::DEFAULT_L {
                f.write_field(Field::L,
                    &LEB128.encode_u32(l as u32)?
                )?;
            }
            if m != GLZ::DEFAULT_M {
                f.write_field(Field::M,
                    &LEB128.encode_u32(m as u32)?
                )?;
            }
            f.write_field(Field::TABLE,
                &(1+GLZ::WIDTH).encode(&table)?
            )?;
        }
        f.write_field(Field::BLOB, &output)?;
    }

    let before = inputs.iter().fold(0, |s, a| s+a.len());
    let after = (output.len()+8-1) / 8;
    println!("compressed {} -> {} ({}%)",
        HumanBytes(before as u64),
        HumanBytes(after as u64),
        (100*(before as i32 - after as i32)) / before as i32
    );
    println!("in ~{}", HumanDuration(time.elapsed()));

    Ok(())
}

fn decode(opt: &DecodeOpt) -> Result<()> {
    // time ourselves
    let time = Instant::now();

    // read file into buffer
    let mut f = File::open(&opt.input)?;
    let mut buf = vec![0u8; 8];
    if !opt.common.no_headers {
        f.read_exact(&mut buf)?;
        if &buf[0..8] != MAGIC {
            bail!("bad magic number in \"{}\"",
                opt.input.to_string_lossy());
        }
    }

    buf.clear();
    let fields: HashMap<Field, &BitSlice> = if opt.common.no_headers {
        let mut fields: HashMap<Field, &BitSlice> = HashMap::new();
        f.read_to_end(&mut buf)?;
        fields.insert(Field::BLOB, &buf.as_bitslice());
        fields
    } else {
        f.read_fields(&mut buf)?
    };

    // get relevant options and defaults
    let l = if let Some(bits) = fields.get(&Field::L) {
        LEB128.decode_u32(bits)?.0 as usize
    } else {
        opt.common.l
    };

    let m = if let Some(bits) = fields.get(&Field::M) {
        LEB128.decode_u32(bits)?.0 as usize
    } else {
        opt.common.m
    };

    let k = if let Some(bits) = fields.get(&Field::K) {
        LEB128.decode_u32(bits)?.0 as usize
    } else if let Some(k) = opt.common.k {
        k
    } else {
        bail!("unknown K, provide -K?")
    };

    let table = if let Some(bits) = fields.get(&Field::TABLE) {
        (1+GLZ::WIDTH).decode(bits)?
    } else if opt.common.table.len() > 0 {
        opt.common.table.clone()
    } else {
        bail!("unknown table, provide --table?")
    };

    let (off, len, name) = if let (Some(off), Some(len)) = (opt.off, opt.len) {
        (off, len, format!("{}..{}", off, len))
    } else if let Some(name) = &opt.file {
        let bits = fields.get(&Field::NAMES).ok_or_else(||
            format!("can't find file \"{}\"", name)
        )?;

        // find our file
        let mut i = 0;
        loop {
            if !(i < bits.len()) {
                bail!("can't find file \"{}\"", name)
            }

            let (namelen, diff) = LEB128.decode_u32_at(bits, i)?;
            let namelen = namelen as usize;
            i += diff;

            let foundname = String::from_utf8(
                8.decode::<u8>(&bits[i..i+8*namelen])?
            ).chain_err(|| "utf8 error in name field")?;
            i += 8*namelen;

            let (off, diff) = LEB128.decode_u32_at(bits, i)?;
            let off = off as usize;
            i += diff;
            let (len, diff) = LEB128.decode_u32_at(bits, i)?;
            let len = len as usize;
            i += diff;

            if name == &foundname {
                break (off, len, foundname)
            }
        }
    } else {
        bail!("what am I decompressing? \
            need either --file or --off and --len");
    };

    let input = if let Some(bits) = fields.get(&Field::BLOB) {
        bits
    } else {
        bail!("no blob?")
    };

    let bound = 2usize.pow(GLZ::WIDTH as u32)
        + 2usize.pow(l as u32)
        + 2usize.pow(m as u32);
    if table.len() != bound {
        bail!("table is incorrect size, found {}, expected {}",
            table.len(), bound);
    }

    println!("K = {}", k);
    if l != GLZ::DEFAULT_L {
        println!("L = {}", l);
    }
    if m != GLZ::DEFAULT_M {
        println!("M = {}", m);
    }
    print!("table = [");
    if opt.common.print_table {
        println!();
        for i in (0..table.len()).step_by(8) {
            print!("    ");
            for j in 0..8 {
                if let Some(x) = table.get(i+j) {
                    print!("0x{:03x}, ", x);
                } else {
                    break;
                }
            }
            println!();
        }
    } else {
        print!("0x{:03x}, 0x{:03x}, 0x{:03x} ... \
                0x{:03x}, 0x{:03x}, 0x{:03x}",
            table[0],
            table[1],
            table[2],
            table[table.len()-3],
            table[table.len()-2],
            table[table.len()-1]
        );
    }
    println!("]");
    println!("file = (\"{}\", {}, {})", name, off, len);

    let glz = GLZ::with_table(k, l, m, &table);
    let output: Vec<u8> = with_prog(
        "decompressing...",
        opt.common.quiet,
        len,
        |prog| {
            glz.decode_at_with_prog(input, off, len, prog)
        }
    )?;

    if let Some(ref outfile) = opt.output {
        fs::write(outfile, &output)?;
    }

    let after = output.len();
    println!("decompressed {}",
        HumanBytes(after as u64),
    );
    println!("in ~{}", HumanDuration(time.elapsed()));

    Ok(())
}

fn ls(opt: &LsOpt) -> Result<()> {
    // read file into buffer
    let mut f = File::open(&opt.input)?;
    let mut buf = vec![0u8; 8];
    if !opt.common.no_headers {
        f.read_exact(&mut buf)?;
        if &buf[0..8] != MAGIC {
            bail!("bad magic number in \"{}\"",
                opt.input.to_string_lossy());
        }
    }

    buf.clear();
    let fields: HashMap<Field, &BitSlice> = if opt.common.no_headers {
        let mut fields: HashMap<Field, &BitSlice> = HashMap::new();
        f.read_to_end(&mut buf)?;
        fields.insert(Field::BLOB, &buf.as_bitslice());
        fields
    } else {
        f.read_fields(&mut buf)?
    };

    // get relevant options and defaults
    let l = if let Some(bits) = fields.get(&Field::L) {
        LEB128.decode_u32(bits)?.0 as usize
    } else {
        opt.common.l
    };

    let m = if let Some(bits) = fields.get(&Field::M) {
        LEB128.decode_u32(bits)?.0 as usize
    } else {
        opt.common.m
    };

    let k = if let Some(bits) = fields.get(&Field::K) {
        LEB128.decode_u32(bits)?.0 as usize
    } else if let Some(k) = opt.common.k {
        k
    } else {
        bail!("unknown K, provide -K?")
    };

    let table = if let Some(bits) = fields.get(&Field::TABLE) {
        (1+GLZ::WIDTH).decode(bits)?
    } else if opt.common.table.len() > 0 {
        opt.common.table.clone()
    } else {
        bail!("unknown table, provide --table?")
    };

    let input = if let Some(bits) = fields.get(&Field::BLOB) {
        bits
    } else {
        bail!("no blob?")
    };

    println!("K = {}", k);
    if l != GLZ::DEFAULT_L {
        println!("L = {}", l);
    }
    if m != GLZ::DEFAULT_M {
        println!("M = {}", l);
    }
    print!("table = [");
    if opt.common.print_table {
        println!();
        for i in (0..table.len()).step_by(8) {
            print!("    ");
            for j in 0..8 {
                if let Some(x) = table.get(i+j) {
                    print!("0x{:03x}, ", x);
                } else {
                    break;
                }
            }
            println!();
        }
    } else {
        print!("0x{:03x}, 0x{:03x}, 0x{:03x} ... \
                0x{:03x}, 0x{:03x}, 0x{:03x}",
            table[0],
            table[1],
            table[2],
            table[table.len()-3],
            table[table.len()-2],
            table[table.len()-1]
        );
    }
    println!("]");

    // print out our file
    let mut total = 0;
    if let Some(bits) = fields.get(&Field::NAMES) {
        let mut i = 0;
        while i < bits.len() {
            let (namelen, diff) = LEB128.decode_u32_at(bits, i)?;
            let namelen = namelen as usize;
            i += diff;

            let foundname = String::from_utf8(
                8.decode::<u8>(&bits[i..i+8*namelen])?
            ).chain_err(|| "utf8 error in name field")?;
            i += 8*namelen;

            let (off, diff) = LEB128.decode_u32_at(bits, i)?;
            let off = off as usize;
            i += diff;
            let (len, diff) = LEB128.decode_u32_at(bits, i)?;
            let len = len as usize;
            i += diff;

            println!("{:>8} {:>8} {}",
                off,
                format!("{}", HumanBytes(len as u64)),
                foundname,
            );

            total += len;
        }
    } else {
        bail!("no file field");
    };

    let before = total;
    let after = (input.len()+8-1) / 8;
    println!("total {} compressed {} ({}%)",
        HumanBytes(before as u64),
        HumanBytes(after as u64),
        (100*(before as i32 - after as i32)) / before as i32,
    );

    Ok(())
}

fn main() {
    let err: Result<()> = match Opt::from_args() {
        Opt::Encode{encode: ref opt} => encode(opt),
        Opt::Decode{decode: ref opt} => decode(opt),
        Opt::Ls    {ls:     ref opt} => ls    (opt),
    };

    if let Err(ref e) = err {
        println!("error: {}", e);

        for e in e.iter().skip(1) {
            println!("caused by: {}", e);
        }

        if let Some(backtrace) = e.backtrace() {
            println!("backtrace: {:?}", backtrace);
        }

        process::exit(1);
    };
}
