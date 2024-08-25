from typing import Tuple

from numba import jit

import pooltool.constants as const


@jit(nopython=True, cache=const.use_numba_cache)
def solve(a: float, b: float, c: float) -> Tuple[float, float]:
    """Solve a quadratic equation At^2 + Bt + C = 0 (just-in-time compiled)"""
    if a == 0:
        u = -c / b
        return u, u
    bp = b / 2
    delta = bp * bp - a * c
    u1 = (-bp - delta**0.5) / a
    u2 = -u1 - b / a
    return u1, u2
