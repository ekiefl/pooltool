#! /usr/bin/env python

import pooltool as pt
import IPython

ipython = IPython.get_ipython()

def old():
    pt.utils.quadratic(*np.random.rand(3))

def new():
    pt.utils.quadratic_fast(*np.random.rand(3))

new()

ipython.magic("timeit old()")
ipython.magic("timeit new()")
