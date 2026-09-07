import pooltool.ptmath.roots.quadratic as quadratic
import pooltool.ptmath.roots.quartic as quartic
from pooltool.ptmath.roots.core import (
    ABS_OR_REL_CUTOFF,
    ATOL,
    RTOL,
    get_real_positive_smallest_root,
    get_real_positive_smallest_roots,
    get_real_smallest_magnitude_root,
    is_real_number,
)

__all__ = [
    "ABS_OR_REL_CUTOFF",
    "ATOL",
    "RTOL",
    "get_real_positive_smallest_root",
    "get_real_positive_smallest_roots",
    "get_real_smallest_magnitude_root",
    "is_real_number",
    "quadratic",
    "quartic",
]
