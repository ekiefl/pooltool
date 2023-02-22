#! /usr/bin/env python

import IPython
import numpy as np

import pooltool as pt

ipython = IPython.get_ipython()


def old():
    pt.utils.coordinate_rotation(np.random.rand(3), 2 * np.pi * np.random.rand())


def new():
    pt.utils.coordinate_rotation_fast(np.random.rand(3), 2 * np.pi * np.random.rand())


new()

ipython.magic("timeit old()")
ipython.magic("timeit new()")

args = (np.random.rand(3), 2 * np.pi * np.random.rand())
output1 = pt.utils.coordinate_rotation(*args)
output2 = pt.utils.coordinate_rotation_fast(*args)
np.testing.assert_allclose(output1, output2)
