import numpy as np
from attrs import astuple


def _array_safe_eq(a, b) -> bool:
    """Check if a and b are equal, even if they are numpy arrays"""
    if a is b:
        return True
    if isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
        return np.array_equal(a, b, equal_nan=True)
    try:
        return a == b
    except TypeError:
        return NotImplemented


def are_dataclasses_equal(dc1, dc2) -> bool:
    """Check if two dataclasses which hold numpy arrays are equal

    This is necessary to avoid ambiguous truthy comparisons, where numpy suggests using
    all() and/or any().
    """
    if dc1 is dc2:
        return True
    if dc1.__class__ is not dc2.__class__:
        return NotImplemented  # better than False
    t1 = astuple(dc1)
    t2 = astuple(dc2)
    return all(_array_safe_eq(a1, a2) for a1, a2 in zip(t1, t2))
