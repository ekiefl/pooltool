#! /usr/bin/env python

import pooltool as pt
import IPython

ipython = IPython.get_ipython()

get_vec = lambda: 10*np.random.rand(3) - 5

def old():
    pt.utils.unit_vector(get_vec())

def new():
    pt.utils.unit_vector_fast(get_vec())

new()

ipython.magic("timeit old()")
ipython.magic("timeit new()")

test_input = get_vec()
output1 = pt.utils.unit_vector(test_input)
output2 = pt.utils.unit_vector_fast(test_input)

assert np.isclose(output1, output2).all()
