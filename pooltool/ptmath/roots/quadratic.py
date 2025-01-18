from typing import Tuple

import numpy as np
from numba import jit

import pooltool.constants as const


@jit(nopython=True, cache=const.use_numba_cache)
def solve(a: float, b: float, c: float) -> Tuple[float, float]:
    """Solve a quadratic equation At^2 + Bt + C = 0 (just-in-time compiled)"""
    if a == 0:
        if b == 0:
            # c=0 => infinite solutions, c≠0 => no solutions
            return np.nan, np.nan
        else:
            # Linear: b * t + c = 0 => t = -c/b
            return -c / b, np.nan

    bp = b / 2
    delta = bp * bp - a * c

    if delta < 0:
        return np.nan, np.nan

    u1 = (-bp - delta**0.5) / a
    u2 = -u1 - b / a
    return u1, u2
