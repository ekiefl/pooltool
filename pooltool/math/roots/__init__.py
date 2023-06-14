from typing import Callable, Dict, Tuple

import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const
import pooltool.math.roots.quartic as quartic
from pooltool.math.roots.quartic import QuarticSolver
from pooltool.terminal import TimeCode

_quartic_routine: Dict[QuarticSolver, Callable] = {
    QuarticSolver.NUMERIC: quartic.solve_many_numerical,
    QuarticSolver.HYBRID: quartic.solve_many,
}


def min_real_root(
    roots: NDArray[np.complex128],
    abs_or_rel_cutoff: float = 1e-3,
    rtol: float = 1e-3,
    atol: float = 1e-9,
) -> np.complex128:
    """Given an array of roots, find the minimum, real, positive root

    Note: This is faster than a numba vector implementation and a numba loop
    implementation.

    Args:
        roots:
            A 1D array of roots.
        abs_or_rel_cutoff:
            The criteria for a root being real depends on the magnitude of it's real
            component. If it's large, we require the imaginary component to be less than
            atol in absolute terms. But when the real component is small, we require the
            imaginary component be less than a fraction, rtol, of the real component.
            This is because when the real component is small, perhaps even comparable to
            atol, using an absolute cutoff for the imaginary component doesn't make much
            sense. abs_or_rel_cutoff defines a threshold for the magnitude of the real
            component, above which atol is used and below which rtol is used.
        atol:
            A root r (with abs(r.real) >= abs_or_rel_cutoff) is considered real if
            abs(r.imag) < atol.
        rtol:
            A root r (with abs(r.real) < abs_or_rel_cutoff) is considered real if
            abs(r.imag) / abs(r.real) < rtol. And in the special case when r.real == 0,
            the root is considered real if r.imag == 0, too.

    Returns:
        root:
            The root determined to be smallest, real, and positive. Note, a complex
            datatype is returned, and it may have residual complex components. Use
            root.real for only the real component.
    """
    positive = roots.real >= 0.0

    imag_mag = np.abs(roots.imag)
    real_mag = np.abs(roots.real)

    big = real_mag > abs_or_rel_cutoff
    big_keep = (imag_mag < atol) & positive

    small = real_mag <= abs_or_rel_cutoff
    small_keep1 = (real_mag > 0) & ((imag_mag / real_mag) < rtol)
    small_keep2 = (real_mag == 0) & (imag_mag == 0)
    small_keep = (small_keep1 | small_keep2) & positive

    candidates = roots[(small & small_keep) | (big & big_keep)]

    if candidates.size == 0:
        return np.complex128(np.inf)

    # Return candidate with the smallest real component
    return candidates[candidates.real.argmin()]


def minimum_quartic_root(
    ps: NDArray[np.float64], solver: QuarticSolver = QuarticSolver.HYBRID
) -> Tuple[float, int]:
    """Solves an array of quartic coefficients, returns smallest, real, positive root

    Args:
        ps:
            A mx5 array of polynomial coefficients, where m is the number of equations.
            The columns are in the order a, b, c, d, e, where these coefficients make up
            the quartic polynomial equation at^4 + bt^3 + ct^2 + dt + e = 0.
        solver:
            The method used to calculate the roots. See
            pooltool.math.roots.quartic.QuarticSolver.

    Returns:
        (real_root, index):
            real_root is the minimum real root from the set of polynomials, and `index`
            specifies the index of the responsible polynomial. i.e. the polynomial with
            the root real_root is ps[index, :]
    """
    # Get the roots for the polynomials
    assert QuarticSolver(solver)
    roots = _quartic_routine[solver](ps)

    best_root = min_real_root(roots.flatten())

    if best_root == np.inf:
        return np.inf, 0

    index = find_first_row_with_value(roots, best_root)
    assert index > -1

    return best_root.real, index


@jit(nopython=True, cache=const.numba_cache)
def find_first_row_with_value(arr, X) -> int:
    """Find the index of the first row in a 2D array that contains a specific value."""
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            if arr[i, j] == X:
                return i
    return -1
