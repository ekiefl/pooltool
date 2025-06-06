import math

import numpy as np
from numba import jit

import pooltool.constants as const


@jit(nopython=True, cache=const.use_numba_cache)
def solve(a: float, b: float, c: float) -> tuple[float, float]:
    """Solve a quadratic equation :math:`A t^2 + B t + C = 0` (just-in-time compiled)"""
    if np.abs(a) < const.EPS:
        if np.abs(b) < const.EPS:
            return math.nan, math.nan
        u = -c / b
        return u, u
    bp = b / 2
    delta = bp * bp - a * c
    u1 = (-bp - delta**0.5) / a
    u2 = -u1 - b / a
    return u1, u2
