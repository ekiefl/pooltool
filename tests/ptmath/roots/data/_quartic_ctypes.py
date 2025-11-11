import ctypes
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

_LIB_PATH = Path(__file__).parent / "_1010_source_code" / "libquartic.so"
_lib = ctypes.CDLL(str(_LIB_PATH))

_lib.oqs_quartic_solver.argtypes = [
    ctypes.POINTER(ctypes.c_double),
    ctypes.POINTER(ctypes.c_double),
]
_lib.oqs_quartic_solver.restype = None


def solve(a: float, b: float, c: float, d: float, e: float) -> NDArray[np.complex128]:
    """Solve quartic equation.

    Args:
        a, b, c, d, e: Coefficients representing at^4 + bt^3 + ct^2 + dt + e = 0

    Returns:
        Array of 4 complex roots
    """
    coeff = np.array([e, d, c, b, a], dtype=np.float64)
    roots = np.zeros(8, dtype=np.float64)

    _lib.oqs_quartic_solver(
        coeff.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        roots.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
    )

    return roots.view(np.complex128)


def solve_many(ps: NDArray[np.float64]) -> NDArray[np.complex128]:
    """Solve multiple quartic equations.

    Args:
        ps: Array of shape (n, 5) where each row is [a, b, c, d, e]
            representing at^4 + bt^3 + ct^2 + dt + e = 0

    Returns:
        Array of shape (n, 4) with complex roots
    """
    num_eqn = ps.shape[0]
    roots = np.zeros((num_eqn, 4), dtype=np.complex128)

    for i in range(num_eqn):
        p = ps[i, :]
        roots[i, :] = solve(p[0], p[1], p[2], p[3], p[4])

    return roots
