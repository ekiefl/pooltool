from typing import Callable, Dict, Tuple

import numpy as np
from numpy.typing import NDArray

import pooltool.math.roots.quartic as quartic
from pooltool.utils.strenum import StrEnum, auto


class QuarticSolver(StrEnum):
    HYBRID = auto()
    NUMERIC = auto()


_routine: Dict[QuarticSolver, Callable] = {
    QuarticSolver.NUMERIC: quartic.solve_many_numerical,
    QuarticSolver.HYBRID: quartic.solve_many,
}


def min_real_root(
    ps: NDArray[np.float64],
    solver: QuarticSolver = QuarticSolver.NUMERIC,
    abs_or_rel_cutoff: float = 1e-3,
    rtol: float = 1e-3,
    atol: float = 1e-9,
) -> Tuple[float, int]:
    """Given an array of polynomial coefficients, find the minimum, real, positive root

    Parameters
    ==========
    ps:
        A mxn array of polynomial coefficients, where m is the number of equations and
        n-1 is the order of the polynomial. If n is 5 (4th order polynomial), the
        columns are in the order a, b, c, d, e, where these coefficients make up the
        polynomial equation at^4 + bt^3 + ct^2 + dt + e = 0
    solver:
        How should the roots be calculated? Choose one of {"numeric",
        "quartic_analytic"}. "numeric" works for n-degree polynomials,
        "quartic_analytic" works for quartics and is fast.
    abs_or_rel_cutoff:
        The criteria for a root being real depends on the magnitude of it's real
        component. If it's large, we require the imaginary component is less than atol
        in absolute terms. But when the real component is small, we require the
        imaginary component be less than a fraction, rtol, of the real component. This
        is because when the real component is small, perhaps even comparable to atol,
        using an absolute cutoff for the imaginary component doesn't make much sense.
        abs_or_rel_cutoff defines a threshold for the magnitude of the real component,
        above which atol is used and below which rtol is used.
    atol:
        A root r (with abs(r.real) >= abs_or_rel_cutoff) is considered real if
        abs(r.imag) < atol.
    rtol:
        A root r (with abs(r.real) < abs_or_rel_cutoff) is considered real if
        abs(r.imag) / abs(r.real) < rtol. And in the special case when r.real == 0, the
        root is considered real if r.imag == 0, too.

    Returns
    =======
    output : (time, index)
        `time` is the minimum real root from the set of polynomials, and `index`
        specifies the index of the responsible polynomial. i.e. the polynomial with the
        root `time` is ps[index, :]
    """
    # Get the roots for the polynomials
    assert QuarticSolver(solver)
    times = _routine[solver](ps)

    negative = times.real < 0.0

    imag_mag = np.abs(times.imag)
    real_mag = np.abs(times.real)

    big_mask = (imag_mag > atol) | negative

    small_discard1 = ((imag_mag / real_mag) > rtol) & (real_mag > 0)
    small_discard2 = (imag_mag != 0) & (real_mag == 0)
    small_mask = small_discard1 | small_discard2 | negative

    times[big_mask & (real_mag > abs_or_rel_cutoff)] = np.inf
    times[small_mask & (real_mag <= abs_or_rel_cutoff)] = np.inf

    # now find the minimum time and the index of the responsible polynomial
    times = np.min(times.real, axis=1)

    return times.min(), times.argmin()
