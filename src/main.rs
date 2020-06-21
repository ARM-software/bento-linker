use glz::bits::*;
use glz::errors::*;
use glz::LEB128;
use glz::GLZ;
use glz::Hist;

use std::io;
use std::fs;
use std::iter;
use std::io::Write;
use std::io::Read;
use std::fs::File;
use std::path::PathBuf;
use std::time::Instant;
use std::thread;
use std::cmp::min;
use std::process;
use std::convert::TryInto;

use error_chain::bail;

use structopt::StructOpt;
use indicatif::ProgressBar;
use indicatif::ProgressStyle;
use indicatif::MultiProgress;
use indicatif::HumanBytes;
use indicatif::HumanDuration;

// Magic info
// [--  32  --][8|8|- 16 -]
//       ^      ^ ^    ^- flags
//       |      | '------ minor version
//       |      '-------- major version
//       '--------------- magic string "\0glz"
//
const MAGIC: [u8; 4] = *b"\0glz";
const VERSION_MAJOR: u8 = 1;
const VERSION_MINOR: u8 = 0;
const VERSION: [u8; 2] = [VERSION_MAJOR, VERSION_MINOR];

// Flags
const FLAG_ARCHIVE : u16 = 0x2000;
const FLAG_INDEX   : u16 = 0x1000;
const FLAG_LEN     : u16 = 0x0400;
const FLAG_K       : u16 = 0x0200;
const FLAG_TABLE   : u16 = 0x0100;
const FLAG_LEB128  : u16 = 0x0001;

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

    /// Max width of reference length in bits. This places an upper-bound
    /// on the size of the Golomb-Rice table (2^8+2^L).
    #[structopt(short = "L", default_value = "4")]
    l: usize,

    /// Width of reference offset nibbles in bits. Note, changing this will
    /// likely break things.
    #[structopt(short = "M", default_value = "4")]
    m: usize,

    /// Limit CLI noise
    #[structopt(short, long)]
    quiet: bool,

    /// Print full Golomb-Rice table, can be useful with --no_headers.
    #[structopt(long)]
    print_table: bool,

    /// Archive mode. Includes filenames in compressed blob and prepends
    /// a list of filename + offset + length triplets. This enables
    /// decompresion via filename.
    #[structopt(short = "A", long)]
    archive: bool,

    /// Index mode. Prepends a list of offset + length tuples. This enables
    /// decompression via index.
    #[structopt(short = "I", long)]
    index: bool,

    /// Don't prepend with magic string, version, and flags used to identify
    /// the file type.
    #[structopt(short = "n", long)]
    no_magic: bool,

    /// Don't prepend with the length of the file after decompression. The
    /// length is only prepended in normal mode, where it is needed to
    /// decompress the file.
    #[structopt(long)]
    no_len: bool,

    /// Don't prepend the K constant. This is needed for decompression.
    #[structopt(long)]
    no_k: bool,

    /// Don't prepend the Golomb-Rice table. This is needed for
    /// decompression.
    #[structopt(long)]
    no_table: bool,

    /// Use LEB128 encoding for any metadata fields. This can reduce the
    /// file size a bit, but requires more complex support at decompression.
    #[structopt(long)]
    leb128: bool,
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
    /// in archive mode.
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
        &'a mut dyn Iterator<Item=(&PathBuf, &usize)>,
        &'a mut dyn FnMut((&PathBuf, &usize)),
        &'a mut dyn FnMut(usize),
    )) -> Result<R>,
{
    if quiet {
        return f((
            &mut iter::repeat((&Default::default(), &0)),
            &mut |_|(),
            &mut |_|()
        ))
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
        let mprog = thread::spawn(move || mprog.join().unwrap());

        let r = f((
            &mut paths.iter().cycle().zip(inputs),
            &mut |(path, input)| {
                prog1.inc(prog2.position());

                let path = path.to_string_lossy();
                prog2.set_message(&path[path.len()-min(path.len(), 20)..]);
                prog2.set_length(*input as u64);
                prog2.reset();
            },
            &mut |diff| {
                prog2.inc(diff as u64);
            }
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
            &mut iter::repeat((&Default::default(), &0)),
            &mut |_| (),
            &mut |diff| {
                prog1.inc(diff as u64);
            }
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
        &'a mut dyn FnMut(usize),
    ) -> Result<R>,
{
    with_prog_all(msg, quiet, &[], &[inputs], |(_, _, prog)| f(prog))
}

// Bit reader/writers
trait WriteBits {
    fn write_bits(
        &mut self,
        bits: &BitSlice
    ) -> Result<()>;

    fn write_size(
        &mut self,
        flags: u16,
        size: usize
    ) -> Result<()>;
}

impl<T: Write> WriteBits for T {
    fn write_bits(
        &mut self,
        bits: &BitSlice
    ) -> Result<()> {
        let mut bits = BitVec::from(bits);
        bits.resize(((bits.len()+8-1)/8)*8, false);
        let bytes = 8usize.decode::<u8>(&bits)?;
        self.write_all(&bytes)?;
        Ok(())
    }

    fn write_size(
        &mut self,
        flags: u16,
        size: usize
    ) -> Result<()> {
        if flags & FLAG_LEB128 != 0 {
            self.write_bits(&LEB128.encode_u32(size as u32)?)?
        } else {
            self.write_all(&(size as u32).to_le_bytes())?
        }
        Ok(())
    }
}

trait ReadBits {
    fn read_size(
        &mut self,
        flags: u16,
    ) -> Result<usize>;
}

impl<T: Read> ReadBits for T {
    fn read_size(
        &mut self,
        flags: u16,
    ) -> Result<usize> {
        if flags & FLAG_LEB128 != 0 {
            let mut buf: Vec<u8> = Vec::new();
            loop {
                let mut c = [0; 1];
                self.read_exact(&mut c)?;
                buf.push(c[0]);
                if c[0] & 0x80 == 0 {
                    break;
                }
            }
            Ok(LEB128.decode_u32(&8.encode::<u8>(&buf)?)?.0 as usize)
        } else {
            let mut buf = [0; 4];
            self.read_exact(&mut buf)?;
            Ok(u32::from_le_bytes(buf) as usize)
        }
    }
}

// Estimator for finding file size without writing anything
enum EstimatorFile {
    Some(File),
    None(u64),
}

impl EstimatorFile {
    fn len(&self) -> io::Result<u64> {
        match self {
            EstimatorFile::Some(f) => Ok(f.metadata()?.len()),
            EstimatorFile::None(s) => Ok(*s)
        }
    }
}

impl Write for EstimatorFile {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        match self {
            EstimatorFile::Some(ref mut f) => f.write(buf),
            EstimatorFile::None(ref mut s) => {
                *s += buf.len() as u64;
                Ok(buf.len())
            }
        }
    }

    fn flush(&mut self) -> io::Result<()> {
        match self {
            EstimatorFile::Some(ref mut f) => f.flush(),
            EstimatorFile::None(_) => Ok(())
        }
    }
}

// Some helpers
fn mkflags(opt: &CommonOpt, mut flags: u16) -> u16 {
    if opt.archive      { flags |= FLAG_ARCHIVE; }
    if opt.index        { flags |= FLAG_INDEX; }
    if flags & (FLAG_ARCHIVE | FLAG_INDEX) == 0 && !opt.no_len
                        { flags |= FLAG_LEN; }
    if !opt.no_k        { flags |= FLAG_K; }
    if !opt.no_table    { flags |= FLAG_TABLE; }
    if opt.leb128       { flags |= FLAG_LEB128; }
    flags
}

fn read_flags<R: Read>(opt: &CommonOpt, f: &mut R) -> Result<u16> {
    // determine flags
    let mut flags = 0u16;
    if !opt.no_magic {
        let mut magic = [0u8; 8];
        f.read_exact(&mut magic)?;
        if &magic[0..4] != MAGIC {
            bail!("bad magic number");
        }
        if &magic[4..6] != VERSION {
            println!("version mismatch (v{}.{} != v{}.{}), \
                trying anyways...",
                magic[4], magic[5],
                VERSION_MAJOR, VERSION_MINOR);
        }

        // set flags with what we find
        flags |= u16::from_le_bytes(magic[6..8].try_into().unwrap());
    }

    // override with explicit flags
    Ok(mkflags(opt, flags))
}

fn print_k(_opt: &CommonOpt, k: usize) {
    println!("K: {}", k);
}

fn print_table(opt: &CommonOpt, table: &[u32]) {
    print!("table: [");
    if opt.print_table {
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
    } else if table.len() < 6 {
        for i in 0..table.len() {
            print!("0x{:03x}{}", table[i],
                    if i != table.len()-1 { ", " } else { "" });
        }
    } else {
        print!("0x{:03x}, 0x{:03x}, 0x{:03x} ... \
                0x{:03x}, 0x{:03x}, 0x{:03x}",
            table[0],
            table[1],
            table[2],
            table[table.len()-3],
            table[table.len()-2],
            table[table.len()-1],
        );
    }
    println!("]");
}

fn print_files(
    _opt: &CommonOpt,
    files: &[(String, usize, usize)],
    blob_size: usize,
) {
    // sort to find the "effective" compression,
    // this isn't perfect but gives a good idea
    let mut files_after = vec![0; files.len()];
    let mut offs: Vec<_> = files.iter()
        .enumerate()
        .map(|(j, (name, off, _))| (off, name, j))
        .collect();
    offs.sort();
    for i in 0..offs.len() {
        let (off, _, j) = offs[i];
        let noff = offs.get(i+1)
            .map(|(noff, _, _)| *noff)
            .unwrap_or(&blob_size);
        files_after[j] = (noff - off + 8-1) / 8;
    }

    println!("files:");
    let namewidth = files.iter()
        .map(|(name, _, _)| name.len())
        .max()
        .map(|width| width+1);
    for ((name, off, before), after) in files.iter().zip(files_after) {
        println!("{:>8} {:<namewidth$} -> {} @ {} ({}%)",
            format!("{}", HumanBytes(*before as u64)),
            name,
            format!("{}", HumanBytes(after as u64)),
            off,
            (100*(*before as i32 - after as i32)) / *before as i32,
            namewidth=namewidth.unwrap()
        );
    }
}

// High-level commands start here
fn encode(opt: &EncodeOpt) -> Result<()> {
    // time ourselves
    let time = Instant::now();

    // read all files into buffers
    let paths: &[PathBuf] = &opt.input;
    let mut inputs: Vec<Vec<u8>> = paths.iter()
        .map(|path| fs::read(path))
        .collect::<io::Result<_>>()?;

    // if we're archiving we need to put our paths in the blob as well
    if opt.common.archive {
        for path in paths {
            let path = path.to_string_lossy();
            inputs.push(Vec::from(path.as_bytes()));
        }
    }

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
    print_k(&opt.common, k);
    print_table(&opt.common, &table);

    // compress!
    let (output, mut ranges) = with_prog_all(
        "compressing...",
        opt.common.quiet,
        &paths,
        &inputs.iter().map(|x| x.len()).collect::<Vec<_>>(),
        |prog| {
            glz.encode_all_with_prog(&inputs, prog)
        }
    )?;

    // adjust offsets for start-of-table?
    if !opt.common.no_table {
        for (off, _) in ranges.iter_mut() {
            *off += (1+GLZ::WIDTH) * table.len();
        }
    }

    let files: Vec<(String, usize, usize)> = paths.iter()
        .zip(ranges.iter())
        .map(|(path, (poff, plen))| (
            String::from(path.to_string_lossy()),
            *poff,
            *plen
        ))
        .collect();
    print_files(&opt.common, &files,
        if !opt.common.no_table { (1+GLZ::WIDTH)*table.len() + output.len() }
        else { output.len() });

    let mut f = if let Some(ref outfile) = opt.output {
        EstimatorFile::Some(File::create(outfile)?)
    } else {
        EstimatorFile::None(0)
    };

    let flags = mkflags(&opt.common, 0);
    if !opt.common.no_magic {
        f.write_all(&MAGIC)?;
        f.write_all(&VERSION)?;
        f.write_all(&flags.to_le_bytes())?;
    }

    if flags & FLAG_ARCHIVE != 0 {
        f.write_size(flags, paths.len())?;
        for ((_path, (poff, plen)), (off, len)) in
                paths.iter()
                    .zip(&ranges[paths.len()..])
                    .zip(&ranges[..paths.len()]) {
            f.write_size(flags, *plen)?;
            f.write_size(flags, *poff)?;
            f.write_size(flags, *len)?;
            f.write_size(flags, *off)?;
        }
    }

    if flags & FLAG_INDEX != 0 {
        f.write_size(flags, paths.len())?;
        for (_path, (off, len)) in paths.iter().zip(ranges) {
            f.write_size(flags, len)?;
            f.write_size(flags, off)?;
        } 
    }

    if flags & FLAG_LEN != 0 {
        f.write_size(flags, inputs.iter()
            .map(|x| x.len())
            .sum())?;
    }

    if flags & FLAG_TABLE != 0 {
        let len = table.len() * (1+GLZ::WIDTH);
        if flags & FLAG_LEB128 != 0 {
            if flags & FLAG_K != 0 { f.write_size(flags, k)?; }
            f.write_size(flags, len)?;
        } else {
            let mut x = 0u32;
            if flags & FLAG_K != 0 { x |= (k as u32) << 24; }
            x |= len as u32;
            f.write_size(flags, x as usize)?;
        }

        f.write_bits(&(1+GLZ::WIDTH).encode(&table)?
                .iter().chain(&output)
                .collect::<BitVec>())?;
    } else {
        if flags & FLAG_K != 0 { f.write_size(flags, k)?; }
        f.write_bits(&output)?;
    }

    let before = inputs[..paths.len()].iter().fold(0, |s, a| s+a.len());
    let after = f.len()?;
    println!("compressed {} -> {} ({}%) in ~{}",
        HumanBytes(before as u64),
        HumanBytes(after as u64),
        (100*(before as i32 - after as i32)) / before as i32,
        HumanDuration(time.elapsed())
    );

    Ok(())
}

fn decode(opt: &DecodeOpt) -> Result<()> {
    // time ourselves
    let time = Instant::now();

    // parse file
    let mut f = File::open(&opt.input)?;
    let flags = read_flags(&opt.common, &mut f)?;

    // load files?
    let mut archive_files: Vec<((usize, usize), (usize, usize))> = Vec::new();
    if flags & FLAG_ARCHIVE != 0 {
        let len = f.read_size(flags)?;
        for _ in 0..len {
            let plen = f.read_size(flags)?;
            let poff = f.read_size(flags)?;
            let len = f.read_size(flags)?;
            let off = f.read_size(flags)?;
            archive_files.push(((poff, plen), (off, len)));
        }
    }

    let mut index_files: Vec<(usize, usize)> = Vec::new();
    if flags & FLAG_INDEX != 0 {
        let len = f.read_size(flags)?;
        for _ in 0..len {
            let len = f.read_size(flags)?;
            let off = f.read_size(flags)?;
            index_files.push((off, len));
        }
    }

    let mut size: Option<usize> = None;
    if flags & FLAG_LEN != 0 {
        size = Some(f.read_size(flags)?);
    }

    // load k/table/blob?
    let mut k: Option<usize> = None;
    let table: Vec<u32>;
    let mut buf: Vec<u8> = Vec::new();
    let blob: &BitSlice;
    let off: usize;
    if flags & FLAG_TABLE != 0 {
        let size;
        if flags & FLAG_LEB128 != 0 {
            if flags & FLAG_K != 0 { k = Some(f.read_size(flags)?); }
            size = f.read_size(flags)?;
        } else {
            let x = f.read_size(flags)? as u32;
            if flags & FLAG_K != 0 { k = Some((x >> 24) as usize); }
            size = (x & 0x00ffffff) as usize;
        }

        f.read_to_end(&mut buf)?;
        table = (1+GLZ::WIDTH).decode(&buf.as_bitslice()[..size])?;
        blob = buf.as_bitslice();
        off = size;
    } else {
        if flags & FLAG_K != 0 { k = Some(f.read_size(flags)? as usize); }
        table = Vec::new();

        f.read_to_end(&mut buf)?;
        blob = buf.as_bitslice();
        off = 0;
    }

    let k = match (k, opt.common.k) {
        (_, Some(k)) => k,
        (Some(k), _) => k,
        _ => bail!("unknown K, provide -K?"),
    };
    let table = match (&table, &opt.common.table) {
        (_, table) if table.len() > 0 => table,
        (table, _) if table.len() > 0 => table,
        _ => bail!("unknown table, provide --table?"),
    };

    print_k(&opt.common, k);
    print_table(&opt.common, table);
    let glz = GLZ::with_table(k, opt.common.l, opt.common.m, table);

    // lookup what we want to decompress
    let (target_off, target_len): (usize, usize) = 'target: loop {
        match (opt.off, opt.len, &opt.file, size) {
            (Some(off), Some(len), _, _) => {
                break 'target (off, len);
            },
            (_, _, Some(file), _) => {
                for ((poff, plen), (off, len)) in archive_files {
                    let name = String::from_utf8(
                        glz.decode_at(&blob, poff, plen)?
                    ).chain_err(|| "utf8 error in name field")?;

                    if &name == file {
                        break 'target (off, len);
                    }
                }

                for (i, (off, len)) in index_files.iter().enumerate() {
                    if &format!("{}", i) == file {
                        break 'target (*off, *len);
                    }
                }

                bail!("file {} not found?", file);
            },
            (_, _, _, Some(size)) => {
                break 'target (off, size);
            },
            _ => {
                bail!("what am I decompressing? \
                    need either --file or --off and --len");
            }
        }
    };
    println!("found file: {} @ {}",
        HumanBytes(target_off as u64),
        target_len);

    let output: Vec<u8> = with_prog(
        "decompressing...",
        opt.common.quiet,
        target_len,
        |prog| {
            glz.decode_at_with_prog(blob, target_off, target_len, prog)
        }
    )?;

    if let Some(ref outfile) = opt.output {
        fs::write(outfile, &output)?;
    }

    let after = output.len();
    println!("decompressed {} in ~{}",
        HumanBytes(after as u64),
        HumanDuration(time.elapsed()),
    );

    Ok(())
}

fn ls(opt: &LsOpt) -> Result<()> {
    // parse file
    let mut f = File::open(&opt.input)?;
    let flags = read_flags(&opt.common, &mut f)?;

    // load files?
    let mut archive_files: Vec<((usize, usize), (usize, usize))> = Vec::new();
    if flags & FLAG_ARCHIVE != 0 {
        let len = f.read_size(flags)?;
        for _ in 0..len {
            let plen = f.read_size(flags)?;
            let poff = f.read_size(flags)?;
            let len = f.read_size(flags)?;
            let off = f.read_size(flags)?;
            archive_files.push(((poff, plen), (off, len)));
        }
    }

    let mut index_files: Vec<(usize, usize)> = Vec::new();
    if flags & FLAG_INDEX != 0 {
        let len = f.read_size(flags)?;
        for _ in 0..len {
            let len = f.read_size(flags)?;
            let off = f.read_size(flags)?;
            index_files.push((off, len));
        }
    }

    let mut size: Option<usize> = None;
    if flags & FLAG_LEN != 0 {
        size = Some(f.read_size(flags)?);
    }

    // load k/table/blob?
    let mut k: Option<usize> = None;
    let table: Vec<u32>;
    let mut buf: Vec<u8> = Vec::new();
    let blob: &BitSlice;
    let off: usize;
    if flags & FLAG_TABLE != 0 {
        let size;
        if flags & FLAG_LEB128 != 0 {
            if flags & FLAG_K != 0 { k = Some(f.read_size(flags)?); }
            size = f.read_size(flags)?;
        } else {
            let x = f.read_size(flags)? as u32;
            if flags & FLAG_K != 0 { k = Some((x >> 24) as usize); }
            size = (x & 0x00ffffff) as usize;
        }

        f.read_to_end(&mut buf)?;
        table = (1+GLZ::WIDTH).decode(&buf.as_bitslice()[..size])?;
        blob = buf.as_bitslice();
        off = size;
    } else {
        if flags & FLAG_K != 0 { k = Some(f.read_size(flags)? as usize); }
        table = Vec::new();

        f.read_to_end(&mut buf)?;
        blob = buf.as_bitslice();
        off = 0;
    }

    let k = match (k, opt.common.k) {
        (_, Some(k)) => k,
        (Some(k), _) => k,
        _ => bail!("unknown K, provide -K?"),
    };
    let table = match (&table, &opt.common.table) {
        (_, table) if table.len() > 0 => table,
        (table, _) if table.len() > 0 => table,
        _ => bail!("unknown table, provide --table?"),
    };

    print_k(&opt.common, k);
    print_table(&opt.common, table);
    let glz = GLZ::with_table(k, opt.common.l, opt.common.m, table);

    // decompress path info
    let mut files: Vec<(String, usize, usize)> = Vec::new();
    for ((poff, plen), (off, len)) in archive_files {
        files.push((
            String::from_utf8(
                glz.decode_at(&blob, poff, plen)?
            ).chain_err(|| "utf8 error in name field")?,
            off,
            len
        ));
    }

    for (off, len) in index_files {
        files.push((format!("{}", off), off, len));
    }

    if let Some(size) = size {
        files.push((format!("0"), off, size));
    }

    print_files(&opt.common, &files, blob.len());

    let before: usize = files.iter().map(|(_, _, len)| len).sum();
    let after = EstimatorFile::Some(f).len()?;
    println!("total compressed {} -> {} ({}%)",
        HumanBytes(before as u64),
        HumanBytes(after as u64),
        (100*(before as i32 - after as i32)) / before as i32,
    );

    Ok(())
}

// Entry point
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
