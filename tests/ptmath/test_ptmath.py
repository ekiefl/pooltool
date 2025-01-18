import numpy as np
import pytest

from pooltool.ptmath.utils import (
    are_points_on_same_side,
    projected_angle,
    solve_transcendental,
)


def test_are_points_on_same_side():
    # Line y = x

    # left side
    assert are_points_on_same_side((0, 0), (1, 1), (0, 1), (1, 2))
    assert are_points_on_same_side((0, 0), (1, 1), (-1, 0), (1, 3))

    # right side
    assert are_points_on_same_side((0, 0), (1, 1), (1, 0), (2, -1))
    assert are_points_on_same_side((0, 0), (1, 1), (10, -20), (1, -2))

    # different sides
    assert not are_points_on_same_side((0, 0), (1, 1), (1, 0), (0, 1))
    assert not are_points_on_same_side((0, 0), (1, 1), (-1, 0), (1, -2))

    # line x = 4

    # left side
    assert are_points_on_same_side((4, 0), (4, 1), (3, 1), (4, -3))
    assert are_points_on_same_side((4, 0), (4, 1), (-10, 1), (-3, -4))

    # left side
    assert are_points_on_same_side((4, 0), (4, 1), (33, 1), (40, -3))
    assert are_points_on_same_side((4, 0), (4, 1), (10, 1), (5, -4))

    # edge cases

    assert are_points_on_same_side((4, 0), (4, 1), (4, 0), (4, 1))
    assert are_points_on_same_side((4, 0), (4, 1), (4, 0), (5, 1))
    assert are_points_on_same_side((4, 0), (4, 1), (4, 0), (3, 1))


def test_transcendental_linear_equation():
    f = lambda x: x - 5  # noqa E731
    root = solve_transcendental(f, 0, 10)
    assert pytest.approx(root, 0.00001) == 5.0


def test_transcendental_nonlinear_equation():
    f = lambda x: x**2 - 4 * x + 3  # noqa E731
    root = solve_transcendental(f, 0, 2.5)
    assert pytest.approx(root, 0.00001) == 1.0


def test_transcendental_no_root_error():
    f = lambda x: x**2 + 1  # noqa E731
    with pytest.raises(ValueError):
        solve_transcendental(f, 0, 10)


def test_projected_angle():
    # 0 starts at <1, 0, 0>
    assert projected_angle(np.array([1, 0, 0])) == 0.0
    assert projected_angle(np.array([0, 1, 0])) == np.pi / 2
    assert projected_angle(np.array([-1, 0, 0])) == np.pi
    assert projected_angle(np.array([0, -1, 0])) == 3 * np.pi / 2
    assert projected_angle(np.array([1, -1, 0])) == 2 * np.pi * (7 / 8)

    # Non-default reference vector
    ref = np.array([0, 1, 0])
    assert projected_angle(np.array([1, 0, 0]), ref) == 3 / 2 * np.pi
    assert projected_angle(np.array([0, 1, 0]), ref) == 0
    assert projected_angle(np.array([-1, 0, 0]), ref) == np.pi / 2

    # Zero returns 0.
    assert projected_angle(np.array([0, 0, 0])) == 0.0

    # Adding z-component doesn't change angle
    assert projected_angle(np.array([1, 0, 1])) == 0.0
    assert projected_angle(np.array([1, 0, 1]), np.array([1, 0, 1])) == 0.0
    assert projected_angle(np.array([0, 1, 1]), np.array([1, 0, 1])) == np.pi / 2
