#! /usr/bin/env python
"""For some reason, `numba_cache` in pooltool/constants.py must be set to False prior to running this script"""

import IPython

import pooltool as pt

# Run once to compile all numba functions. By doing this,
# compilation times will be excluded in the timing.
system = pt.System(path="benchmark_short.pkl")
system.simulate(continuize=False, quiet=True)


def setup_and_run():
    system = pt.System(path="benchmark_short.pkl")
    system.simulate(continuize=False, quiet=True)


ipython = IPython.get_ipython()
ipython.magic("timeit setup_and_run()")
