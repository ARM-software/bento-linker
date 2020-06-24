use serial_test::serial;
use std::os::unix::fs::PermissionsExt;
use std::error;
use std::fs;
use std::process;

#[test]
fn cli_help_text_test() -> Result<(), Box<dyn error::Error>> {
    // mostly a sanity check that the test framework works
    let status = process::Command::new("./target/debug/glz")
        .output()?.status;
    assert!(!status.success());
    Ok(())
}

#[test]
#[serial]
fn cli_encode_decode_test() -> Result<(), Box<dyn error::Error>> {
    // try to compress/decompress each of the data*.txt files we have
    let mut paths: Vec<_> = fs::read_dir("./examples")?
        .filter_map(|f| f.ok())
        .map(|f| f.path())
        .filter(|path|
            path.is_file() &&
            path.file_name()
                .and_then(|x| x.to_str())
                .map(|x| x.starts_with("data"))
                .unwrap_or(false) &&
            path.extension()
                .and_then(|x| x.to_str())
                .map(|x| x == "txt")
                .unwrap_or(false))
        .map(|path| {
            let mut path_glz = path.clone();
            path_glz.set_extension("glz");
            let mut path_out = path.clone();
            path_out.set_extension("out");
            (path, path_glz, path_out)
        })
        .collect();
    paths.sort();

    for (path_txt, path_glz, path_out) in &paths {
        let path_txt = path_txt.to_str().unwrap();
        let path_glz = path_glz.to_str().unwrap();
        let path_out = path_out.to_str().unwrap();

        let status = process::Command::new("./target/debug/glz")
            .args(&["encode", "-q", path_txt, "-o", path_glz])
            .status()?;
        assert!(status.success());
        let status = process::Command::new("./target/debug/glz")
            .args(&["ls", "-q", path_glz])
            .status()?;
        assert!(status.success());
        let status = process::Command::new("./target/debug/glz")
            .args(&["decode", "-q", path_glz, "-o", path_out])
            .status()?;
        assert!(status.success());
        let status = process::Command::new("diff")
            .args(&["-q", "-s", path_txt, path_out])
            .status()?;
        assert!(status.success());
    }
    Ok(())
}

#[test]
#[serial]
fn cli_encode_decode_index_test() -> Result<(), Box<dyn error::Error>> {
    // try to compress/decompress each of the data*.txt files we have
    let mut paths: Vec<_> = fs::read_dir("./examples")?
        .filter_map(|f| f.ok())
        .map(|f| f.path())
        .filter(|path|
            path.is_file() &&
            path.file_name()
                .and_then(|x| x.to_str())
                .map(|x| x.starts_with("data"))
                .unwrap_or(false) &&
            path.extension()
                .and_then(|x| x.to_str())
                .map(|x| x == "txt")
                .unwrap_or(false))
        .map(|path| {
            let mut path_glz = path.clone();
            path_glz.set_extension("glz");
            let mut path_out = path.clone();
            path_out.set_extension("out");
            (path, path_glz, path_out)
        })
        .collect();
    paths.sort();

    for (path_txt, path_glz, path_out) in &paths {
        let path_txt = path_txt.to_str().unwrap();
        let path_glz = path_glz.to_str().unwrap();
        let path_out = path_out.to_str().unwrap();

        let status = process::Command::new("./target/debug/glz")
            .args(&["encode", "-q", "-I", path_txt, "-o", path_glz])
            .status()?;
        assert!(status.success());
        let status = process::Command::new("./target/debug/glz")
            .args(&["ls", "-q", path_glz])
            .status()?;
        assert!(status.success());
        let status = process::Command::new("./target/debug/glz")
            .args(&["decode", "-q", "-f", "0", path_glz, "-o", path_out])
            .status()?;
        assert!(status.success());
        let status = process::Command::new("diff")
            .args(&["-q", "-s", path_txt, path_out])
            .status()?;
        assert!(status.success());
    }
    Ok(())
}

#[test]
#[serial]
fn cli_encode_decode_archive_test() -> Result<(), Box<dyn error::Error>> {
    // try to compress/decompress each of the data*.txt files we have
    let mut paths: Vec<_> = fs::read_dir("./examples")?
        .filter_map(|f| f.ok())
        .map(|f| f.path())
        .filter(|path|
            path.is_file() &&
            path.file_name()
                .and_then(|x| x.to_str())
                .map(|x| x.starts_with("data"))
                .unwrap_or(false) &&
            path.extension()
                .and_then(|x| x.to_str())
                .map(|x| x == "txt")
                .unwrap_or(false))
        .map(|path| {
            let mut path_glz = path.clone();
            path_glz.set_extension("glz");
            let mut path_out = path.clone();
            path_out.set_extension("out");
            (path, path_glz, path_out)
        })
        .collect();
    paths.sort();

    for (path_txt, path_glz, path_out) in &paths {
        let path_txt = path_txt.to_str().unwrap();
        let path_glz = path_glz.to_str().unwrap();
        let path_out = path_out.to_str().unwrap();

        let status = process::Command::new("./target/debug/glz")
            .args(&["encode", "-q", "-A", path_txt, "-o", path_glz])
            .status()?;
        assert!(status.success());
        let status = process::Command::new("./target/debug/glz")
            .args(&["ls", "-q", path_glz])
            .status()?;
        assert!(status.success());
        let status = process::Command::new("./target/debug/glz")
            .args(&["decode", "-q", "-f", path_txt, path_glz, "-o", path_out])
            .status()?;
        assert!(status.success());
        let status = process::Command::new("diff")
            .args(&["-q", "-s", path_txt, path_out])
            .status()?;
        assert!(status.success());
    }
    Ok(())
}

#[test]
#[serial]
fn cli_example_decoders_test() -> Result<(), Box<dyn error::Error>> {
    // try to compress/decompress each of the data*.txt files we have
    let mut paths: Vec<_> = fs::read_dir("./examples")?
        .filter_map(|f| f.ok())
        .map(|f| f.path())
        .filter(|path|
            path.is_file() &&
            path.file_name()
                .and_then(|x| x.to_str())
                .map(|x| x.starts_with("data"))
                .unwrap_or(false) &&
            path.extension()
                .and_then(|x| x.to_str())
                .map(|x| x == "txt")
                .unwrap_or(false))
        .map(|path| {
            let mut path_glz = path.clone();
            path_glz.set_extension("glz");
            let mut path_out = path.clone();
            path_out.set_extension("out");
            (path, path_glz, path_out)
        })
        .collect();
    paths.sort();

    // use the decoders we find in examples
    let mut decoders: Vec<_> = fs::read_dir("./examples")?
        .filter_map(|f| f.ok())
        .map(|f| f.path())
        .filter(|path|
            path.is_file() &&
            path.file_name()
                .and_then(|x| x.to_str())
                .map(|x| x.starts_with("decoder"))
                .unwrap_or(false) &&
            path.metadata()
                .map(|x| x.permissions().mode() & 0o001 != 0)
                .unwrap_or(false))
        .collect();
    decoders.sort();

    let status = process::Command::new("make")
        .args(&["-C", "examples"])
        .status()?;
    assert!(status.success());

    for (path_txt, path_glz, _) in &paths {
        let path_txt = path_txt.to_str().unwrap();
        let path_glz = path_glz.to_str().unwrap();

        let status = process::Command::new("./target/debug/glz")
            .args(&["encode", "-q", "-n", path_txt, "-o", path_glz])
            .status()?;
        assert!(status.success());
    }

    for decoder in &decoders {
        for (path_txt, path_glz, path_out) in &paths {
            let path_txt = path_txt.to_str().unwrap();
            let path_glz = path_glz.to_str().unwrap();
            let path_out = path_out.to_str().unwrap();

            let status = process::Command::new(decoder)
                .arg(path_glz)
                .stdout(process::Stdio::from(fs::File::create(path_out)?))
                .status()?;
            assert!(status.success());
            let status = process::Command::new("diff")
                .args(&["-q", "-s", path_txt, path_out])
                .status()?;
            assert!(status.success());
        }
    }

    Ok(())
}
