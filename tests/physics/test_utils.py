import numpy as np
import pytest
from numpy.typing import NDArray

from pooltool.physics.utils import get_airborne_time


@pytest.mark.parametrize(
    "rvw,R,g,expected",
    [
        # Case 1: Without gravity, time is infinite
        (
            np.array(
                [
                    [0.0, 0.0, 1.1],  # r_0
                    [0.0, 0.0, 0.0],  # v_0
                    [0.0, 0.0, 0.0],  # w_0
                ],
                dtype=np.float64,
            ),
            0.1,
            0.0,
            np.inf,
        ),
        # Case 2: Drop from apex, time is sqrt(2/g * (r_0z - R))
        (
            np.array(
                [
                    [0.0, 0.0, 1.1],
                    [0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0],
                ],
                dtype=np.float64,
            ),
            0.1,
            10.0,
            0.4472135955,
        ),
        # Case 3: Variant of case 2: x- and y- velocity doesn't affect answer
        (
            np.array(
                [
                    [0.0, 0.0, 1.1],
                    [1.0, 1.0, 0.0],
                    [0.0, 0.0, 0.0],
                ],
                dtype=np.float64,
            ),
            0.1,
            10.0,
            0.4472135955,
        ),
    ],
)
def test_get_airborne_time(
    rvw: NDArray[np.float64], R: float, g: float, expected: float
):
    t_f = get_airborne_time(rvw, R, g)
    if np.isinf(expected):
        assert np.isinf(t_f), f"Expected {expected}, got {t_f}"
    else:
        assert np.isclose(t_f, expected), f"Expected {expected}, got {t_f}"
