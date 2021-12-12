#! /usr/bin/env python

import pooltool as pt
import IPython

ipython = IPython.get_ipython()

def old():
    p = np.random.rand(250).reshape((50, 5))
    pt.utils.min_real_root(p)

def new():
    p = np.random.rand(250).reshape((50, 5))
    pt.utils.min_real_root_fast(p)

new()

ipython.magic("timeit old()")
ipython.magic("timeit new()")

p = np.random.rand(250).reshape((50, 5))
output1 = pt.utils.min_real_root(p)
output2 = pt.utils.min_real_root_fast(p)

np.testing.assert_allclose(output1, output2)
