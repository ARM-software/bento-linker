**&lt;runtime&gt;-rsa** - This example uses [MbedTLS][mbedtls] to perform
asymmetric encryption/decryption using RSA-pkcs1. There are three different
boxes active here, one box containing the MbedTLS logic, and two other boxe
acting as Alice and Bob sharing encrypted messages with each other.

This is intended to showcase how a system may keep sensitive secrets in its
own box, and instead reference these secrets with file-descriptor-esque ids
The ability to bind unique identifiers to imports helps quite a bit here.

Unfortunately, due to WebAssembly page size issues, this example only works
with the native runtimes.

More info in the [README.md](/README.md).

[mbedtls]: https://github.com/ARMmbed/mbedtls
