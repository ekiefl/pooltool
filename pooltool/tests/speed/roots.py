#! /usr/bin/env python

import IPython
import numpy as np

import pooltool as pt

ipython = IPython.get_ipython()


def old():
    p = np.random.rand(250).reshape((50, 5))
    pt.utils.roots(p)


def new():
    p = np.random.rand(250).reshape((50, 5))
    pt.utils.roots_fast(p)


new()

ipython.magic("timeit old()")
ipython.magic("timeit new()")

p = np.random.rand(250).reshape((50, 5))
output1 = pt.utils.roots(p)
output2 = pt.utils.roots_fast(p)

np.testing.assert_allclose(np.sort(output1.real, axis=1), np.sort(output2.real, axis=1))
assert np.isclose(np.sort(output1.imag, axis=1), np.sort(output2.imag, axis=1)).all()
