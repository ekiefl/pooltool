from numba import jit

import pooltool.constants as const


@jit(nopython=True, cache=const.numba_cache)
def solve(a, b, c):
    """Solve a quadratic equation At^2 + Bt + C = 0 (just-in-time compiled)"""
    a = complex(a)
    b = complex(b)
    c = complex(c)

    if a == 0:
        u = -c / b
        return u, u
    bp = b / 2
    delta = bp * bp - a * c
    u1 = (-bp - delta**0.5) / a
    u2 = -u1 - b / a
    return u1, u2
