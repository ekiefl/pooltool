from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from pooltool.ptmath.roots._quartic_numba import solve_many

TEST_DIR = Path(__file__).parent


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
    coeffs = np.load(TEST_DIR / "hard_quartic_coeffs.npy")

    true_roots_array = np.load(TEST_DIR / "hard_quartic_coeffs.roots.npy")
    computed_roots_array = solve_many(coeffs[:, ::-1])

    for i in range(len(coeffs)):
        computed_roots, true_roots = match_roots(
            computed_roots_array[i], true_roots_array[i]
        )
        assert np.allclose(computed_roots, true_roots, rtol=1e-3)


def test_coefficients_ground_truth():
    coeffs = np.load(TEST_DIR / "quartic_coeffs.npy")

    true_roots_array = np.load(TEST_DIR / "quartic_coeffs.roots.npy")
    computed_roots_array = solve_many(coeffs[:, ::-1])

    for i in range(len(coeffs)):
        computed_roots, true_roots = match_roots(
            computed_roots_array[i], true_roots_array[i]
        )
        assert np.allclose(computed_roots, true_roots, rtol=1e-15)
