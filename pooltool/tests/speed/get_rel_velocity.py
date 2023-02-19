#! /usr/bin/env python

import IPython
import numpy as np

import pooltool as pt

ipython = IPython.get_ipython()

get_rvw = lambda: np.random.rand(9).reshape((3, 3))


def old():
    pt.utils.get_rel_velocity(get_rvw(), 0.0285)


def new():
    pt.utils.get_rel_velocity_fast(get_rvw(), 0.0285)


new()

ipython.magic("timeit old()")
ipython.magic("timeit new()")

test_input = get_rvw()
output1 = pt.utils.get_rel_velocity(test_input, 0.0285)
output2 = pt.utils.get_rel_velocity_fast(test_input, 0.0285)

assert np.isclose(output1, output2).all()
