import numpy as np
from numpy.typing import NDArray

from pooltool.ptmath.roots._quartic_numba import solve_many as solve_many_numba
from pooltool.ptmath.roots.core import (
    get_real_positive_smallest_roots,
)

_solver = solve_many_numba


def solve_quartics(ps: NDArray[np.float64]) -> NDArray[np.float64]:
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
    return get_real_positive_smallest_roots(_solver(ps))
