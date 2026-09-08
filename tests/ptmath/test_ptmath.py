import numpy as np
import pytest

from pooltool.ptmath.utils import (
    angle_between_vectors,
    are_points_on_same_side,
    decompose_normal_tangent,
    rotation_from_vector_to_vector,
    rotation_matrix_from_vector_to_vector,
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
    f = lambda x: x - 5
    root = solve_transcendental(f, 0, 10)
    assert pytest.approx(root, 0.00001) == 5.0


def test_transcendental_nonlinear_equation():
    f = lambda x: x**2 - 4 * x + 3
    root = solve_transcendental(f, 0, 2.5)
    assert pytest.approx(root, 0.00001) == 1.0


def test_transcendental_no_root_error():
    f = lambda x: x**2 + 1
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


@pytest.mark.parametrize(
    "vector, normal, expected_v_n, expected_v_t, expected_tangent",
    [
        (
            np.array([1.0, 2.0, 0.0]),
            np.array([1.0, 0.0, 0.0]),
            1.0,
            2.0,
            np.array([0.0, 1.0, 0.0]),
        ),
        (
            np.array([-1.0, 2.0, 0.0]),  # Reverse x-direction compared to above
            np.array([1.0, 0.0, 0.0]),
            -1.0,
            2.0,
            np.array([0.0, 1.0, 0.0]),
        ),
        (
            np.array([1.0, 1.0, 1.0]),
            np.array([1.0, 1.0, 0.0]) / np.sqrt(2),
            np.sqrt(2),
            1.0,
            np.array([0.0, 0.0, 1.0]),
        ),
        (
            np.array([1.0, 0.0, 0.0]),
            np.array([1.0, 0.0, 0.0]),
            1.0,
            0.0,
            np.array([0.0, 0.0, 0.0]),  # indeterminate tangent direction
        ),
    ],
)
def test_decompose_normal_tangent(
    vector, normal, expected_v_n, expected_v_t, expected_tangent
):
    v_n, v_t, tangent = decompose_normal_tangent(vector, normal)
    assert np.isclose(v_n, expected_v_n), f"normal={normal}, tangent={tangent}"
    assert np.isclose(v_t, expected_v_t), f"normal={normal}, tangent={tangent}"
    assert np.allclose(tangent, expected_tangent)


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


@pytest.mark.parametrize(
    "a, b",
    [
        # x-axis to y-axis, a 90 degree rotation about z
        (np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0])),
        # Parallel vectors of different length, should give the identity
        (np.array([1.0, 0.0, 0.0]), np.array([2.0, 0.0, 0.0])),
        # Generic non-unit vectors
        (np.array([1.0, 2.0, 3.0]), np.array([4.0, 5.0, 6.0])),
        # x-axis to z-axis, orthogonal vectors
        (np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0])),
        # Antiparallel along a coordinate axis, cross product is exactly zero
        (np.array([0.0, 0.0, 1.0]), np.array([0.0, 0.0, -1.0])),
        # Antiparallel off-axis, exercises the perpendicular axis selection
        (np.array([0.3, -0.4, 0.5]), np.array([-0.6, 0.8, -1.0])),
        # Nearly parallel, a small but non-degenerate rotation
        (np.array([1.0, 0.0, 0.0]), np.array([1.0, 1e-3, 0.0])),
    ],
)
def test_rotation_matrix_from_vector_to_vector(a, b):
    m = rotation_matrix_from_vector_to_vector(a, b)

    assert m @ m.T == pytest.approx(np.eye(3))
    assert np.linalg.det(m) == pytest.approx(1.0)

    rotated = m @ a
    assert rotated / np.linalg.norm(rotated) == pytest.approx(b / np.linalg.norm(b))
    assert m.T @ rotated == pytest.approx(a)
