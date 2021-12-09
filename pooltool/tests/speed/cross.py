#! /usr/bin/env python

import pooltool as pt
import IPython

ipython = IPython.get_ipython()

def old():
    pt.utils.cross(np.random.rand(3), np.random.rand(3))

def new():
    pt.utils.cross_fast(np.random.rand(3), np.random.rand(3))

new()

ipython.magic("timeit old()")
ipython.magic("timeit new()")

args = np.random.rand(3), np.random.rand(3)
output1 = pt.utils.cross(*args)
output2 = pt.utils.cross_fast(*args)

assert np.isclose(output1, output2).all()
