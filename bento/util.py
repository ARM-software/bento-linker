import itertools as it
import string

# some convenience functions
def arbitrary():
    """
    Generates arbitrary names for variable generation.
    a-b, aa-bb, aaa-bbb, and so on.
    """
    for i in it.count(1):
        yield from map(''.join, it.product(string.ascii_lowercase, repeat=i))
