from typing import Callable, Dict

import numpy as np

import pooltool.math.roots.quartic as quartic
from pooltool.utils.strenum import StrEnum, auto


class QuarticSolver(StrEnum):
    NEW = auto()
    OLD = auto()


_routine: Dict[QuarticSolver, Callable] = {
    QuarticSolver.OLD: quartic.solve_many_numerical,
    QuarticSolver.NEW: quartic.solve_many,
}


def min_real_root(p, solver: QuarticSolver = QuarticSolver.OLD, tol=1e-9):
    """Given an array of polynomial coefficients, find the minimum real root

    Parameters
    ==========
    p:
        A mxn array of polynomial coefficients, where m is the number of equations and
        n-1 is the order of the polynomial. If n is 5 (4th order polynomial), the
        columns are in the order a, b, c, d, e, where these coefficients make up the
        polynomial equation at^4 + bt^3 + ct^2 + dt + e = 0
    solver:
        How should the roots be calculated? Choose one of {"numeric",
        "quartic_analytic"}. "numeric" works for n-degree polynomials,
        "quartic_analytic" works for quartics and is fast.
    tol:
        Roots are real if their imaginary components are less than than tol.

    Returns
    =======
    output : (time, index)
        `time` is the minimum real root from the set of polynomials, and `index`
        specifies the index of the responsible polynomial. i.e. the polynomial with the
        root `time` is p[index]
    """
    # Get the roots for the polynomials
    assert QuarticSolver(solver)
    times = _routine[solver](p)

    # If the root has a nonzero imaginary component, set to infinity
    # If the root has a nonpositive real component, set to infinity
    times[(abs(times.imag) > tol) | (times.real <= tol)] = np.inf

    # now find the minimum time and the index of the responsible polynomial
    times = np.min(times.real, axis=1)

    return times.min(), times.argmin()
