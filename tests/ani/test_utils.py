import numpy as np
import pytest

import pooltool.ani.utils as autils


def test_as_quaternion_starts_at_the_identity_and_stays_there_without_spin():
    w = np.zeros((5, 3))
    t = np.arange(5) * 0.1

    quats = autils.as_quaternion(w, t)

    assert quats.shape == (5, 4)
    assert np.array_equal(quats, np.tile([1.0, 0.0, 0.0, 0.0], (5, 1)))


def test_as_quaternion_accumulates_a_constant_spin_about_z():
    rate = np.pi
    w = np.tile([0.0, 0.0, rate], (11, 1))
    t = np.linspace(0.0, 1.0, 11)

    quats = autils.as_quaternion(w, t)

    half_angles = 0.5 * rate * t
    expected = np.column_stack(
        [np.cos(half_angles), np.zeros(11), np.zeros(11), np.sin(half_angles)]
    )
    assert quats == pytest.approx(expected)
    assert np.linalg.norm(quats, axis=1) == pytest.approx(np.ones(11))
