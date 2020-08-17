Note, some of the extra libraries take a while to compile (LLVM). You may
consider instead downloading their recent releases here:
- wasi-sdk - https://github.com/WebAssembly/wasi-sdk/releases/tag/wasi-sdk-8

  In ./extra:
  ``` bash
  wget https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-8/wasi-sdk-8.0-linux.tar.gz
  tar xvfz wasi-sdk-8.0-linux.tar.gz
  ln -s wasi-sdk-8.0 wasi-sdk
  ```

- wabt - https://github.com/WebAssembly/wabt/releases

  In ./extra:
  ``` bash
  wget https://github.com/WebAssembly/wabt/releases/download/1.0.19/wabt-1.0.19-ubuntu.tar.gz
  tar xvfz wabt-1.0.19-ubuntu.tar.gz
  ln -s wabt-1.0.19 wabt
  ```
