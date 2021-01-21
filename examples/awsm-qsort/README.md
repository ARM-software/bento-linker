**&lt;runtime&gt;-qsort** - This examples performas quick-sort on an
array on integers.

```
array: [5255, 850, 974, ... 586, 336, 7677]
calling qsort N=10000...
result: 0
array: [2, 3, 4, ... 9998, 9998, 9998]
```

It's a fairly simple example, but a good showcase of performance in
tight loops with memory accesses.

It also showcases using `__box_<name>_push/pop` to allocate memory
inside the box.

The largest input is 10K ints.

More info in the [README.md](/README.md).
