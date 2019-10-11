use error_chain::error_chain;

error_chain! {
    foreign_links {
        Utf8(::std::string::FromUtf8Error);
        IO(::std::io::Error);
    }

    errors {}
}
