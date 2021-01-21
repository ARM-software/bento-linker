## GLZ

A compression algorithm designed for extremely lightweight decompression.

GLZ, or Granular Lempel-Ziv, is an approach to granular compression
built through careful application of Lempel-Ziv in order to maintain
O(1) RAM consumption and O(n) decompression cost. GLZ combines this with
Golomb-Rice codes to create a compact, granular compression where slices
are _very_ cheap to decompress.

More info on the encoding can be found in [glz.rs](src/glz.rs).

