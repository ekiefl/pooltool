import numpy as np
import pytest
import quaternion

from pooltool.ptmath.utils import (
    angle_between_vectors,
    are_points_on_same_side,
    quaternion_from_vector_to_vector,
    rotation_from_vector_to_vector,
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


def test_angle_between_vectors_basic():
    # Test orthogonal vectors
    v1 = np.array([1.0, 0.0, 0.0])
    v2 = np.array([0.0, 1.0, 0.0])
    angle = angle_between_vectors(v1, v2)
    assert pytest.approx(angle) == np.pi / 2

    # Test parallel vectors
    v1 = np.array([1.0, 0.0, 0.0])
    v2 = np.array([2.0, 0.0, 0.0])
    angle = angle_between_vectors(v1, v2)
    assert pytest.approx(angle) == 0.0

    # Test antiparallel vectors
    v1 = np.array([1.0, 0.0, 0.0])
    v2 = np.array([-1.0, 0.0, 0.0])
    angle = angle_between_vectors(v1, v2)
    assert pytest.approx(angle) == np.pi

    # Test 45 degree angle
    v1 = np.array([1.0, 0.0, 0.0])
    v2 = np.array([1.0, 1.0, 0.0])
    angle = angle_between_vectors(v1, v2)
    assert pytest.approx(angle) == np.pi / 4


def test_rotation_from_vector_to_vector():
    # Test rotation from x-axis to y-axis
    v1 = np.array([1.0, 0.0, 0.0])
    v2 = np.array([0.0, 1.0, 0.0])
    rotation = rotation_from_vector_to_vector(v1, v2)

    # Apply rotation to v1 and check it matches v2
    rotated = rotation.apply(v1)
    assert np.allclose(rotated, v2)

    # Apply rotation and check direction is preserved
    normalized_rotated = rotated / np.linalg.norm(rotated)
    normalized_v2 = v2 / np.linalg.norm(v2)
    assert np.allclose(normalized_rotated, normalized_v2)

    # Test that rotation preserves magnitude when applied to unit vectors
    v1_unit = v1 / np.linalg.norm(v1)
    v2_unit = v2 / np.linalg.norm(v2)
    rotation = rotation_from_vector_to_vector(v1_unit, v2_unit)
    rotated_unit = rotation.apply(v1_unit)
    assert np.allclose(np.linalg.norm(rotated_unit), 1.0)


def test_quaternion_from_vector_to_vector():
    # Test rotation from x-axis to y-axis
    v1 = np.array([1.0, 0.0, 0.0])
    v2 = np.array([0.0, 1.0, 0.0])
    q = quaternion_from_vector_to_vector(v1, v2)

    # Check that it's a valid unit quaternion
    assert pytest.approx(np.linalg.norm(quaternion.as_float_array(q))) == 1.0

    # Test parallel vectors (should give identity quaternion)
    v1 = np.array([1.0, 0.0, 0.0])
    v2 = np.array([2.0, 0.0, 0.0])
    q = quaternion_from_vector_to_vector(v1, v2)

    # For parallel vectors, should be close to identity quaternion (1, 0, 0, 0)
    # The real part should be close to 1
    assert pytest.approx(abs(q.w)) == 1.0

    # Test that quaternion has unit magnitude
    v1 = np.array([1.0, 2.0, 3.0])
    v2 = np.array([4.0, 5.0, 6.0])
    q = quaternion_from_vector_to_vector(v1, v2)
    assert pytest.approx(np.linalg.norm(quaternion.as_float_array(q))) == 1.0

    # Test orthogonal vectors
    v1 = np.array([1.0, 0.0, 0.0])
    v2 = np.array([0.0, 0.0, 1.0])
    q = quaternion_from_vector_to_vector(v1, v2)

    # For 90 degree rotation, real part should be cos(pi/4) = sqrt(2)/2
    assert pytest.approx(abs(q.w), abs=1e-10) == np.sqrt(2) / 2
