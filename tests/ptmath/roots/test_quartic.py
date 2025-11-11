from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from pooltool.ptmath.roots._quartic_numba import solve_many

TEST_DIR = Path(__file__).parent
DATA_DIR = TEST_DIR / "data"


def match_roots(
    computed_roots: NDArray[np.complex128],
    true_roots: NDArray[np.complex128],
) -> tuple[NDArray[np.complex128], NDArray[np.complex128]]:
    computed = computed_roots.copy()
    true = true_roots.copy()

    matched_computed = []
    matched_true = []

    for t_root in true:
        distances = np.abs(computed - t_root)
        min_idx = np.argmin(distances)
        matched_computed.append(computed[min_idx])
        matched_true.append(t_root)
        computed = np.delete(computed, min_idx)

    return np.array(matched_computed), np.array(matched_true)


def test_hard_coefficients_ground_truth():
    coeffs = np.load(DATA_DIR / "hard_quartic_coeffs.npy")

    true_roots_array = np.load(DATA_DIR / "hard_quartic_coeffs.roots.npy")
    computed_roots_array = solve_many(coeffs[:, ::-1])

    for i in range(len(coeffs)):
        computed_roots, true_roots = match_roots(
            computed_roots_array[i], true_roots_array[i]
        )
        assert np.allclose(computed_roots, true_roots, rtol=1e-3)


def test_coefficients_ground_truth():
    coeffs = np.load(DATA_DIR / "quartic_coeffs.npy")

    true_roots_array = np.load(DATA_DIR / "quartic_coeffs.roots.npy")
    computed_roots_array = solve_many(coeffs[:, ::-1])

    for i in range(len(coeffs)):
        computed_roots, true_roots = match_roots(
            computed_roots_array[i], true_roots_array[i]
        )
        assert np.allclose(computed_roots, true_roots, rtol=1e-15)


def test_1010_reference():
    coeffs = np.load(DATA_DIR / "1010_reference_coeffs.npy")
    c_roots_array = np.load(DATA_DIR / "1010_reference_coeffs.roots.npy")

    numba_roots_array = solve_many(coeffs)

    for i in range(len(coeffs)):
        numba_roots, c_roots = match_roots(numba_roots_array[i], c_roots_array[i])
        assert np.allclose(numba_roots, c_roots, rtol=1e-15, atol=1e-15)
