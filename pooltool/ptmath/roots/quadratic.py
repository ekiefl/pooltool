import cmath
from typing import Tuple

import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const


@jit(nopython=True, cache=const.use_numba_cache)
def solve_old(a: float, b: float, c: float) -> Tuple[float, float]:
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


@jit(nopython=True, cache=const.use_numba_cache)
def solve(a: float, b: float, c: float) -> NDArray[np.complex128]:
    _a = complex(a)
    _b = complex(b)
    _c = complex(c)

    roots = np.full(2, np.nan, dtype=np.complex128)

    if abs(_a) != 0:
        # Quadratic case
        d = _b * _b - 4 * _a * _c
        sqrt_d = cmath.sqrt(d)

        # Sign trick to reduce catastrophic cancellation
        sign_b = 1.0 if _b.real >= 0 else -1.0

        r1_num = -_b - sign_b * sqrt_d
        r1_den = 2 * _a

        # Fallback if numerator is tiny
        if abs(r1_num) < 1e-14 * abs(r1_den):
            r1_num = -_b + sign_b * sqrt_d

        r1 = r1_num / r1_den

        # Use product identity for x2
        if abs(r1) < 1e-14:
            r2 = (-_b + sqrt_d) / (2 * _a)
        else:
            r2 = (_c / _a) / r1

        roots[0] = r1
        roots[1] = r2
        return roots

    if abs(_b) != 0:
        # Linear case
        r1 = -_c / _b
        roots[0] = r1
        return roots

    # Equation is just c=0. Either zero or infinite solutions. Returns nans
    return roots
