import numpy as np
from numba import jit
from numpy.typing import NDArray

from pooltool import constants as const


@jit(nopython=True, cache=const.use_numba_cache)
def get_real_positive_smallest_root(
    roots: NDArray[np.complex128],
    abs_or_rel_cutoff: float = 1e-3,
    rtol: float = 1e-3,
    atol: float = 1e-9,
) -> float:
    """Returns the smallest positive and real root from a set of roots.

    Args:
        roots:
            A 1D array of n polynomial roots.
        abs_or_rel_cutoff:
            The criteria for a root being real depends on the magnitude of its real
            component. If it's large, we require the imaginary component to be less than
            atol in absolute terms. But when the real component is small, we require the
            imaginary component be less than a fraction, rtol, of the real component.
            abs_or_rel_cutoff defines a threshold for the magnitude of the real
            component, above which atol is used and below which rtol is used.
        atol:
            A root r (with abs(r.real) >= abs_or_rel_cutoff) is considered real if
            abs(r.imag) < atol.
        rtol:
            A root r (with abs(r.real) < abs_or_rel_cutoff) is considered real if
            abs(r.imag) / abs(r.real) < rtol. And in the special case when r.real == 0,
            the root is considered real if r.imag == 0, too.

    Returns:
        The smallest root that is real and positive. If no such root exists (e.g. all
        roots are complex or negative), then `np.inf` is returned.
    """
    min_root = np.inf

    for i in range(len(roots)):
        root = roots[i]
        root_real = root.real
        root_imag = root.imag

        if root_real < 0.0:
            continue

        imag_mag = abs(root_imag)
        real_mag = abs(root_real)

        is_real = False
        if real_mag > abs_or_rel_cutoff:
            is_real = imag_mag < atol
        elif real_mag > 0:
            is_real = (imag_mag / real_mag) < rtol
        else:
            is_real = imag_mag == 0.0

        if is_real and root_real < min_root:
            min_root = root_real

    return min_root


@jit(nopython=True, cache=const.use_numba_cache)
def get_real_positive_smallest_roots(
    roots: NDArray[np.complex128],
    abs_or_rel_cutoff: float = 1e-3,
    rtol: float = 1e-3,
    atol: float = 1e-9,
) -> NDArray[np.float64]:
    """Returns the smallest postive and real root for each set of roots.

    Args:
        roots:
            A mxn array of polynomial root solutions, where m is the number of equations
            and n is the order of the polynomial.
        abs_or_rel_cutoff:
            The criteria for a root being real depends on the magnitude of its real
            component. If it's large, we require the imaginary component to be less than
            atol in absolute terms. But when the real component is small, we require the
            imaginary component be less than a fraction, rtol, of the real component.
            abs_or_rel_cutoff defines a threshold for the magnitude of the real
            component, above which atol is used and below which rtol is used.
        atol:
            A root r (with abs(r.real) >= abs_or_rel_cutoff) is considered real if
            abs(r.imag) < atol.
        rtol:
            A root r (with abs(r.real) < abs_or_rel_cutoff) is considered real if
            abs(r.imag) / abs(r.real) < rtol. And in the special case when r.real == 0,
            the root is considered real if r.imag == 0, too.

    Returns:
            An array of shape m. Each value is the smallest root that is real and
            positive. If no such root exists (e.g. all roots are complex), then
            `np.inf` is used.
    """
    num_sets = roots.shape[0]
    result = np.empty(num_sets, dtype=np.float64)

    for i in range(num_sets):
        result[i] = get_real_positive_smallest_root(
            roots[i, :], abs_or_rel_cutoff, rtol, atol
        )

    return result
