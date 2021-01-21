**&lt;runtime&gt;-littlefs** - This example runs the [LittleFS][littlefs]
filesystem inside its own box, using import/exports to communicate with
a simulated block device.

The example itself does a few things:

1. Updates a boot count.

2. Logs a value to a rotate-based log, renaming the log file
   every 1000 updates.

To simulate rebooting, the box is clobbered every 10K updates. This happens
10 times for a total of 100K updates.

This example is a good showcase of a real-world import/export heavy use case
with relatively complex logic. It's a good example of where adopting
bento-boxes could be valuable for protected a system from
difficult-to-bugproof code.

More info in the [README.md](/README.md).

[littlefs]: https://github.com/ARMmbed/littlefs
