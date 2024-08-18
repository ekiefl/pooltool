import numpy as np
from numpy.typing import NDArray


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

    # Find the minimum real positive root in each row
    min_real_positive_roots = np.min(processed_roots.real, axis=1)

    return min_real_positive_roots
