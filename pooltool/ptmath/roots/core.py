import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const


@jit(nopython=True, cache=const.use_numba_cache)
def filter_non_physical_roots(
    roots: NDArray[np.complex128],
    abs_or_rel_cutoff: float = 1e-3,
    rtol: float = 1e-3,
    atol: float = 1e-9,
) -> NDArray[np.complex128]:
    """Filters out non-physical roots from a 1D array of roots for a polynomial.

    Filters a 1D array of complex roots, allowing only those with a non-negative real part
    and an acceptably small imaginary part (by absolute or relative tolerance).
    All other roots are replaced with np.inf (of dtype complex128).

    Args:
        roots:
            A 1D array of complex roots to be filtered.
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
        A 1D array of the same shape as `roots`, where non-physical (negative or
        “too imaginary”) roots are replaced by `np.inf + 0j`, and valid roots
        remain unchanged.
    """
    processed_roots = np.full(len(roots), np.inf, dtype=np.complex128)

    for i in range(len(roots)):
        root = roots[i]

        if root.real < 0:
            continue

        # Root has positive real component

        imag_mag = np.abs(root.imag)
        real_mag = np.abs(root.real)

        if real_mag > abs_or_rel_cutoff:
            # Real component is "big" -- treat with absolute tolerances
            if imag_mag <= atol:
                processed_roots[i] = root
        else:
            # Real component is "small" -- treat with relative tolerances
            if real_mag > 0 and (imag_mag / real_mag) < rtol:
                processed_roots[i] = root
            elif real_mag == 0 and imag_mag == 0:
                processed_roots[i] = root

    return processed_roots


def filter_non_physical_roots_many(
    roots: NDArray[np.complex128],
    abs_or_rel_cutoff: float = 1e-3,
    rtol: float = 1e-3,
    atol: float = 1e-9,
) -> NDArray[np.complex128]:
    """Filters out non-physical roots from a 2D array of roots for many polynomials.

    Vectorized version of filtering complex roots, preserving only those whose real part
    is non-negative and whose imaginary part is sufficiently small by either absolute or
    relative criteria. All other roots are replaced with np.inf.

    Similar logic to `filter_non_physical_roots` but applied element-wise to a
    multi-dimensional array of roots.

    Args:
        roots:
            An array of complex numbers, for example shape (m, n), where each
            row might correspond to all roots of one polynomial.
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
        An array (dtype np.complex128) of the same shape as `roots` (e.g. (m, n)) where
        the non-physical (negative-real or too-imaginary) entries are replaced by
        `np.inf`.
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

    is_real = (small & small_keep) | (big & big_keep)
    processed_roots = np.where(is_real, roots, np.complex128(np.inf))

    return processed_roots


def get_smallest_physical_root_many(
    roots: NDArray[np.complex128],
    abs_or_rel_cutoff: float = 1e-3,
    rtol: float = 1e-3,
    atol: float = 1e-9,
) -> NDArray[np.float64]:
    """Returns the smallest postive and real root for each set of roots.

    Args:
        roots:
            An array of shape (m, n) of polynomial root solutions, where m is the number
            of equations and n is the order of the polynomial.
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
        An array of shape (m,). Values are the smallest root that is real and positive.
        If no such root exists (e.g. all roots are complex), then `np.inf` is used.
    """

    processed_roots = filter_non_physical_roots_many(
        roots, abs_or_rel_cutoff, rtol, atol
    )

    # Find the minimum real positive root in each row
    min_real_positive_roots = np.min(processed_roots.real, axis=-1)

    return min_real_positive_roots


def get_sorted_physical_roots(
    roots: NDArray[np.complex128],
    abs_or_rel_cutoff: float = 1e-3,
    rtol: float = 1e-3,
    atol: float = 1e-9,
) -> NDArray[np.float64]:
    """Returns roots sorted by smallest, postive, and real.

    Args:
        roots:
            An array of shape (m, n) of polynomial root solutions, where m is the number
            of equations and n is the order of the polynomial.
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
        An array of shape (m,). Values are the smallest root that is real and positive.
        Columns are sorted by smallest real positive root. Negative and imaginary roots
        are converted to infinity.
    """

    processed_roots = filter_non_physical_roots_many(
        roots, abs_or_rel_cutoff, rtol, atol
    )

    sorted_real_positive_roots = np.sort(processed_roots.real, axis=-1)

    return sorted_real_positive_roots
