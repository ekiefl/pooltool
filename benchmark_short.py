#! /usr/bin/env python

import pooltool as pt
import IPython

# Run once to compile all numba functions. By doing this,
# compilation times will be excluded in the timing.
system = pt.System(path='benchmark_short.pkl')
system.simulate(continuize=False, quiet=True)

def setup_and_run():
    system = pt.System(path='benchmark_short.pkl')
    system.simulate(continuize=False, quiet=True)

ipython = IPython.get_ipython()
ipython.magic("timeit setup_and_run()")
