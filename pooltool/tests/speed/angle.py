#! /usr/bin/env python

import IPython
import numpy as np

import pooltool as pt

ipython = IPython.get_ipython()


def old():
    pt.utils.angle(np.random.rand(2), np.random.rand(2))


def new():
    pt.utils.angle_fast(np.random.rand(2), np.random.rand(2))


new()

ipython.magic("timeit old()")
ipython.magic("timeit new()")
