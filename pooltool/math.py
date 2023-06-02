from math import acos

import numpy as np
from numba import jit

import pooltool.constants as c


def wiggle(x, val):
    """Vary a float or int x by +- val according to a uniform distribution"""
    return x + val * (2 * np.random.rand() - 1)


@jit(nopython=True, cache=c.numba_cache)
def cross(u, v):
    """Compute cross product u x v, where u and v are 3-dimensional vectors

    (just-in-time compiled)

    Notes
    =====
    - Speed comparison in pooltool/tests/speed/cross.py
    """
    return np.array(
        [
            u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0],
        ]
    )


@jit(nopython=True, cache=c.numba_cache)
def quadratic(a, b, c):
    """Solve a quadratic equation At^2 + Bt + C = 0 (just-in-time compiled)

    Notes
    =====
    - Speed comparison in pooltool/tests/speed/quadratic.py
    """
    if a == 0:
        u = -c / b
        return u, u
    bp = b / 2
    delta = bp * bp - a * c
    u1 = (-bp - delta**0.5) / a
    u2 = -u1 - b / a
    return u1, u2
