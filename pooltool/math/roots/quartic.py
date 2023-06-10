from typing import Tuple

import numpy as np
import sympy
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const


@jit(nopython=True, cache=const.numba_cache)
def solve_many(ps: NDArray[np.float64]) -> NDArray[np.complex128]:
    roots, indicators = _solve_many(ps.astype(np.complex128))
    return roots


@jit(nopython=True, cache=const.numba_cache)
def _solve_many(
    ps: NDArray[np.complex128],
) -> Tuple[NDArray[np.complex128], NDArray[np.uint8]]:
    num_eqn = ps.shape[0]

    all_roots = np.zeros((num_eqn, 4), dtype=np.complex128)
    indicators = np.zeros(num_eqn, dtype=np.uint8)

    for i in range(num_eqn):
        all_roots[i, :], indicators[i] = _solve(ps[i, :])

    return all_roots, indicators


@jit(nopython=True, cache=const.numba_cache)
def solve(p: NDArray[np.float64]) -> NDArray[np.complex128]:
    return _solve(p.astype(np.complex128))[0]


@jit(nopython=True, cache=const.numba_cache)
def _solve(p: NDArray[np.complex128]) -> Tuple[NDArray[np.complex128], int]:
    # Guess which of the two isomorphic polynomial equations is more likely to be
    # numerically stable
    reverse = instability(p[::-1]) < instability(p)

    # Solve that polynomial first
    if reverse:
        soln_1 = 1.0 / analytic(p[::-1])
    else:
        soln_1 = analytic(p)

    # Check whether the solved roots are genuine
    for root in soln_1:
        if abs(evaluate(p, root)) > const.EPS:
            break
    else:
        return soln_1, 0

    # The roots were bad. Try the other polynomial equation
    if reverse:
        soln_2 = analytic(p)
    else:
        soln_2 = 1.0 / analytic(p[::-1])

    # Check whether the solved roots are genuine
    for root in soln_2:
        if abs(evaluate(p, root)) > const.EPS:
            break
    else:
        return soln_2, 1

    # The roots were bad. Resorting to companion matrix eigenvalues
    return numeric(p), 2


@jit(nopython=True, cache=const.numba_cache)
def evaluate(p: NDArray[np.complex128], val: complex) -> complex:
    return p[0] * val**4 + p[1] * val**3 + p[2] * val**2 + p[3] * val + p[4]


@jit(nopython=True, cache=const.numba_cache)
def instability(p: NDArray[np.complex128]) -> float:
    """Range is from [0, inf], 0 is most stable"""
    a, b = p[:2]

    if a == 0 or b == 0:
        return 0.0

    t = abs(a / b)
    return t + 1 / t


@jit(nopython=True, cache=const.numba_cache)
def numeric(p: NDArray[np.complex128]) -> NDArray[np.complex128]:
    return np.roots(p)


@jit(nopython=True, cache=const.numba_cache)
def analytic(p: NDArray[np.complex128]) -> NDArray[np.complex128]:
    # Convert to complex so we can take cubic root of negatives
    a, b, c, d, e = p

    x0 = 1 / a
    x1 = c * x0
    x2 = a ** (-2)
    x3 = b**2
    x4 = x2 * x3
    x5 = x1 - 3 * x4 / 8
    x6 = x5**3
    x7 = d * x0
    x8 = b * x2
    x9 = c * x8
    x10 = a ** (-3)
    x11 = b**3 * x10
    x12 = (x11 / 8 + x7 - x9 / 2) ** 2
    x13 = -d * x8 / 4 + e * x0
    x14 = c * x10 * x3 / 16 + x13 - 3 * b**4 / (256 * a**4)
    x15 = -x12 / 8 + x14 * x5 / 3 - x6 / 108
    x16 = 2 * x15 ** (1 / 3)
    x17 = x11 / 4 + 2 * x7 - x9
    x18 = 2 * x1 / 3 - x2 * x3 / 4
    x19 = np.sqrt(-x16 - x18)
    x20 = x17 / x19
    x21 = 4 * x1 / 3
    x22 = -x21 + x4 / 2
    x23 = np.sqrt(x16 + x20 + x22) / 2
    x24 = x19 / 2
    x25 = b * x0 / 4
    x26 = x24 + x25
    x27 = -(c**2) * x2 / 12 - x13
    x28 = (
        x12 / 16 - x14 * x5 / 6 + x6 / 216 + np.sqrt(x15**2 / 4 + x27**3 / 27)
    ) ** (1 / 3) or const.EPS
    x29 = 2 * x28
    x30 = 2 * x27 / (3 * x28)
    x31 = -x29 + x30
    x32 = np.sqrt(-x18 - x31) or const.EPS
    x33 = x17 / x32
    x34 = np.sqrt(x22 + x31 + x33) / 2
    x35 = x32 / 2
    x36 = x25 + x35
    x37 = -x2 * x3 / 2 + x21
    x38 = np.sqrt(x16 - x20 - x37) / 2
    x39 = np.sqrt(-x29 + x30 - x33 - x37) / 2
    x40 = -x25

    if abs(e / a - b * d / (4 * a**2) + c**2 / (12 * a**2)) < const.EPS:
        roots = (
            -x23 - x26,
            x23 - x26,
            x24 - x25 - x38,
            x24 + x38 + x40,
        )
    else:
        roots = (
            -x34 - x36,
            x34 - x36,
            -x25 + x35 - x39,
            x35 + x39 + x40,
        )

    return np.array(roots, dtype=np.complex128)


def _truth(a_val, b_val, c_val, d_val, e_val, digits=50):
    x, a, b, c, d, e = sympy.symbols("x a b c d e")
    general_solution = sympy.solve(a * x**4 + b * x**3 + c * x**2 + d * x + e, x)
    return [
        sol.evalf(digits, subs={a: a_val, b: b_val, c: c_val, d: d_val, e: e_val})
        for sol in general_solution
    ]
