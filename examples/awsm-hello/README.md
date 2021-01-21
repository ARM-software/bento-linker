**&lt;runtime&gt;-hello** - A simple hello world example that brings up
two boxes that each print a hello world message.

```
testing box printf
box1 says hello!
box2 says hello!
return values: 0 0
```

This example also tests a simple export, import, and an abort.

This is the best example to start with when adding a new runtime.

Why two boxes? Three boxes doesn't fit on this device with the current
WebAssembly page size limitations (64KiB page vs 256KiB available RAM).
Note this is something possible to fix in the WebAssembly spec.

More info in the [README.md](/README.md).
