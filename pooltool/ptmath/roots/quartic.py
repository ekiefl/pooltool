from typing import Callable, Dict, Tuple

import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const
from pooltool.ptmath.roots.core import (
    get_real_positive_smallest_roots,
)
from pooltool.utils.strenum import StrEnum, auto


class QuarticSolver(StrEnum):
    HYBRID = auto()
    NUMERIC = auto()


def solve_quartics(
    ps: NDArray[np.float64], solver: QuarticSolver = QuarticSolver.HYBRID
) -> NDArray[np.float64]:
    """Returns the smallest positive and real root for each quartic polynomial.

    Args:
        ps:
            A mx5 array of polynomial coefficients, where m is the number of equations.
            The columns are in the order a, b, c, d, e, where these coefficients make up
            the quartic polynomial equation at^4 + bt^3 + ct^2 + dt + e = 0.
        solver:
            The method used to calculate the roots. See
            pooltool.ptmath.roots.quartic.QuarticSolver.

    Returns:
        roots:
            An array of shape m. Each value is the smallest root that is real and
            positive. If no such root exists (e.g. all roots have complex), then
            `np.inf` is returned.
    """
    # Get the roots for the polynomials
    assert QuarticSolver(solver)

    roots = _quartic_routine[solver](ps)  # Shape m x 4, dtype complex128
    best_roots = get_real_positive_smallest_roots(roots)  # Shape m, dtype float64

    return best_roots


def solve_many_numerical(p: NDArray[np.float64]) -> NDArray[np.complex128]:
    """Solve multiple polynomial equations using companion matrix eigenvalues

    This is a vectorized implementation of numpy.roots that can solve multiple
    polynomials in a vectorized fashion. The solution is taken from this wonderful
    stackoverflow answer: https://stackoverflow.com/a/35853977

    Args:
        p:
            A mxn array of polynomial coefficients, where m is the number of equations
            and n-1 is the order of the polynomial. If n is 5 (4th order polynomial),
            the columns are in the order a, b, c, d, e, where these coefficients make up
            the polynomial equation at^4 + bt^3 + ct^2 + dt + e = 0

    Notes:
        - Not yet amenable to numbaization (0.56.4). Problem is the numba implementation of
          np.linalg.eigvals, which only supports 2D arrays, but the strategy here is to pass
          np.lingalg.eigvals as a vectorized 3D array. Nevertheless, here is a numba
          implementation that is just slightly slower (7% slower) than this function:

              n = p.shape[-1]
              A = np.zeros(p.shape[:1] + (n - 1, n - 1), dtype=np.complex128)
              A[:, 1:, :-1] = np.eye(n - 2)
              p0 = np.copy(p[:, 0]).reshape((-1, 1))
              A[:, 0, :] = -p[:, 1:] / p0
              roots = np.zeros((p.shape[0], n - 1), dtype=np.complex128)
              for i in range(p.shape[0]):
                  roots[i, :] = np.linalg.eigvals(A[i, :, :])
              return roots
    """
    n = p.shape[-1]
    A = np.zeros(p.shape[:1] + (n - 1, n - 1), np.float64)
    A[..., 1:, :-1] = np.eye(n - 2)
    A[..., 0, :] = -p[..., 1:] / p[..., None, 0]
    return np.linalg.eigvals(A)  # type: ignore


def solve_many(ps: NDArray[np.float64]) -> NDArray[np.complex128]:
    """Solve multiple quartic equations using analytical solutions when possible

    Closed-form analytical solutions exist for the quartic polynomial equation, but can
    suffer from severe numerical instability. Fortunately, the quality of an
    analytically calculated roots can be determined by plugging them back into the
    quartic and ensuring they evaluate the function to 0.

    This function calculates roots to a quartic by analytically solving the quartic
    polynomials. If the roots are inaccurate, an isomorphic polynomial is solved
    analytically. If those roots are also inaccurate, the roots are solved using the
    companion matrix eigenvalue method, which is very reliable, but slower.

    Args:
        p:
            A mx5 array of polynomial coefficients, where m is the number of equations.
            The columns are in the order a, b, c, d, e, where these coefficients make up
            the polynomial equation at^4 + bt^3 + ct^2 + dt + e = 0
    """
    roots, _ = _solve_many(ps.astype(np.complex128))
    return roots


@jit(nopython=True, cache=const.use_numba_cache)
def solve(a: float, b: float, c: float, d: float, e: float) -> NDArray[np.complex128]:
    return _solve(np.array([a, b, c, d, e], dtype=np.complex128))[0]


@jit(nopython=True, cache=const.use_numba_cache)
def _solve_many(
    ps: NDArray[np.complex128],
) -> Tuple[NDArray[np.complex128], NDArray[np.uint8]]:
    num_eqn = ps.shape[0]

    all_roots = np.zeros((num_eqn, 4), dtype=np.complex128)
    indicators = np.zeros(num_eqn, dtype=np.uint8)

    for i in range(num_eqn):
        all_roots[i, :], indicators[i] = _solve(ps[i, :])

    return all_roots, indicators


@jit(nopython=True, cache=const.use_numba_cache)
def _solve(
    p: NDArray[np.complex128], ftol: float = 1e-5
) -> Tuple[NDArray[np.complex128], int]:
    """Solve a quartic with mixed strategy

    Args:
        ftol:
            This is a very sensitive parameter and controls whether or not the
            analytically calculated roots sufficiently satisfy the polynomial. After
            much testing, I've determined that when the root evaluates to <1e-5, it's
            nearly always numerically similar to the true root. I didn't find any bad
            roots that evaluate to <1e-5. I did find good/decent roots evaluating to
            >1e-5, but I'm happy to play it conservative and keep it at 1e-5--those
            roots will always be caught by the numerical solution.
    """

    e = p[-1].real

    # This means t=0 is a root. No point solving the other roots, just return all 0s
    if e == 0.0:
        return np.zeros(4, dtype=np.complex128), 0

    # Round-off error seems to be especially problematic for analytic solutions when e
    # is small
    if abs(e) < 1e-7:
        return numeric(p), 3

    # The analytic solutions don't like 0s
    if (p == 0).any():
        return numeric(p), 3

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
        if abs(evaluate(p, root)) > ftol:
            break
    else:
        return soln_1, 1

    # The roots were bad. Try the other polynomial equation
    if reverse:
        soln_2 = analytic(p)
    else:
        soln_2 = 1.0 / analytic(p[::-1])

    # Check whether the solved roots are genuine
    for root in soln_2:
        if abs(evaluate(p, root)) > ftol:
            break
    else:
        return soln_2, 2

    # The roots were bad. Resorting to companion matrix eigenvalues
    return numeric(p), 3


@jit(nopython=True, cache=const.use_numba_cache)
def evaluate(p: NDArray[np.complex128], val: complex) -> complex:
    return p[0] * val**4 + p[1] * val**3 + p[2] * val**2 + p[3] * val + p[4]


@jit(nopython=True, cache=const.use_numba_cache)
def instability(p: NDArray[np.complex128]) -> float:
    """Range is from [0, inf], 0 is most stable"""
    a, b = p[:2]

    if a == 0 or b == 0:
        return 0.0

    t = abs(a / b)
    return t + 1 / t


@jit(nopython=True, cache=const.use_numba_cache)
def numeric(p: NDArray[np.complex128]) -> NDArray[np.complex128]:
    return np.roots(p).astype(np.complex128)


@jit(nopython=True, cache=const.use_numba_cache)
def analytic(p: NDArray[np.complex128]) -> NDArray[np.complex128]:
    """Calculate a quartic's roots using the closed-form solution

    This function was created with the help of sympy.

    To start, I solved the general quartic polynomial roots:

    >>> from sympy import symbols, Eq, solve
    >>> x, a, b, c, d, e = symbols('x a b c d e')
    >>> general_solution = solve(a*x**4 + b*x**3 + c*x**2 + d*x + e, x)

    This yields 4 expressions, one for each root. Each expression is piecewise
    conditional, where if the following equality is true, the first expression is used,
    and otherwise the second expression is used.

    >>> general_solution[0].args[0][1]
    Eq(e/a - b*d/(4*a**2) + c**2/(12*a**2), 0)

    So in total there are 8 expressions, 2 for each root, and the expression used for
    each root is determined based on whether the above equality holds true. These
    expressions are huge, so to better digest them, I used the following common
    subexpression elimination:

    >>> from sympy import cse
    >>> cse(
    >>>     [
    >>>         general_solution[0].args[0][0],
    >>>         general_solution[0].args[1][0],
    >>>         general_solution[1].args[0][0],
    >>>         general_solution[1].args[1][0],
    >>>         general_solution[2].args[0][0],
    >>>         general_solution[2].args[1][0],
    >>>         general_solution[3].args[0][0],
    >>>         general_solution[3].args[1][0],
    >>>     ]
    >>> )

    Then I used a vim macro to convert these subexpressions into the lines of python
    code you see below.
    """

    # Convert to complex so we can take cubic root of negatives
    a, b, c, d, e = p

    if e == 0:
        return np.array([0, np.nan, np.nan, np.nan], dtype=np.complex128)

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
    x28 = (x12 / 16 - x14 * x5 / 6 + x6 / 216 + np.sqrt(x15**2 / 4 + x27**3 / 27)) ** (
        1 / 3
    ) or const.EPS
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
    import sympy  # type: ignore

    x, a, b, c, d, e = sympy.symbols("x a b c d e")
    general_solution = sympy.solve(a * x**4 + b * x**3 + c * x**2 + d * x + e, x)
    return [
        sol.evalf(digits, subs={a: a_val, b: b_val, c: c_val, d: d_val, e: e_val})
        for sol in general_solution
    ]


_quartic_routine: Dict[QuarticSolver, Callable] = {
    QuarticSolver.NUMERIC: solve_many_numerical,
    QuarticSolver.HYBRID: solve_many,
}
