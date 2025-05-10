import numpy as np
import pytest

from pooltool.ptmath.utils import surface_velocity, tangent_surface_velocity


def test_surface_velocity_no_angular_velocity():
    R = 0.05715
    v = np.array([1.0, 2.0, 3.0])
    rvw = np.array([np.zeros(3), v, np.zeros(3)], dtype=np.float64)
    unit_direction = np.array([1.0, 0.0, 0.0])

    v_surface = surface_velocity(rvw, unit_direction, R)
    assert np.allclose(v_surface, v, atol=1e-6), (
        "with no angular velocity, v_surface should equal v"
    )


def test_surface_velocity_no_linear_velocity():
    R = 0.05715
    w = np.array([1.0, 2.0, 3.0])
    rvw = np.array([np.zeros(3), np.zeros(3), w], dtype=np.float64)
    unit_direction = np.array([1.0, 0.0, 0.0])
    w_tangent = w - np.linalg.vecdot(w, unit_direction) * unit_direction

    v_surface = surface_velocity(rvw, unit_direction, R)
    s_surface = np.linalg.vector_norm(v_surface)
    s_surface_expected = np.linalg.vector_norm(w_tangent) * R
    assert np.isclose(s_surface, s_surface_expected, atol=1e-6), (
        "with no linear velocity, surface speed should equal magnitude "
        "of tangential angular velocity times radius"
    )


def test_tangent_surface_velocity_no_angular_velocity():
    R = 0.05715
    v = np.array([1.0, 2.0, 3.0])
    rvw = np.array([np.zeros(3), v, np.zeros(3)], dtype=np.float64)
    unit_direction = np.array([1.0, 0.0, 0.0])
    v_tangent = v - np.linalg.vecdot(v, unit_direction) * unit_direction

    v_surface_tangent = tangent_surface_velocity(rvw, unit_direction, R)
    assert np.allclose(v_surface_tangent, v_tangent, atol=1e-6), (
        "with no angular velocity, tangent surface velocity should equal velocity tangent to unit"
    )


def test_tangent_surface_velocity_no_linear_velocity():
    R = 0.05715
    w = np.array([1.0, 2.0, 3.0])
    rvw = np.array([np.zeros(3), np.zeros(3), w], dtype=np.float64)
    unit_direction = np.array([1.0, 0.0, 0.0])
    w_tangent = w - np.linalg.vecdot(w, unit_direction) * unit_direction

    v_surface = tangent_surface_velocity(rvw, unit_direction, R)
    s_surface = np.linalg.vector_norm(v_surface)
    s_surface_expected = np.linalg.vector_norm(w_tangent) * R
    assert np.isclose(s_surface, s_surface_expected, atol=1e-6), (
        "with no linear velocity, tangent surface speed should equal magnitude of tangential angular velocity times radius"
    )


@pytest.mark.parametrize(
    "v,w,d,expected_surface,expected_tangent",
    [
        (
            # v -> +y, w -> +z, d -> +z
            np.array([0.0, 1.0, 0.0]),
            np.array([0.0, 0.0, 1.0]),
            np.array([0.0, 0.0, 1.0]),
            # Surface
            np.array([0.0, 1.0, 0.0]),
            # Surface tangent
            np.array([0.0, 1.0, 0.0]),
        ),
        (
            # v -> +y, w -> +z, d -> -z
            np.array([0.0, 1.0, 0.0]),
            np.array([0.0, 0.0, 1.0]),
            np.array([0.0, 0.0, -1.0]),
            # Surface
            np.array([0.0, 1.0, 0.0]),
            # Surface tangent
            np.array([0.0, 1.0, 0.0]),
        ),
        (
            # v -> +y, w -> +z, d -> +x
            np.array([0.0, 1.0, 0.0]),
            np.array([0.0, 0.0, 1.0]),
            np.array([1.0, 0.0, 0.0]),
            # Surface
            np.array([0.0, 2.0, 0.0]),
            # Surface tangent
            np.array([0.0, 2.0, 0.0]),
        ),
        (
            # v -> +y, w -> +z, d -> -x
            np.array([0.0, 1.0, 0.0]),
            np.array([0.0, 0.0, 1.0]),
            np.array([-1.0, 0.0, 0.0]),
            # Surface
            np.array([0.0, 0.0, 0.0]),
            # Surface tangent
            np.array([0.0, 0.0, 0.0]),
        ),
        (
            # v -> +y, w -> +z, d -> -y
            np.array([0.0, 1.0, 0.0]),
            np.array([0.0, 0.0, 1.0]),
            np.array([0.0, -1.0, 0.0]),
            # Surface
            np.array([1.0, 1.0, 0.0]),
            # Surface tangent
            np.array([1.0, 0.0, 0.0]),
        ),
        (
            # v -> +y & +z, w -> +z, d -> -y
            np.array([0.0, 1.0, 1.0]),
            np.array([0.0, 0.0, 1.0]),
            np.array([0.0, -1.0, 0.0]),
            # Surface
            np.array([1.0, 1.0, 1.0]),
            # Surface tangent
            np.array([1.0, 0.0, 1.0]),
        ),
        (
            # v -> +y & +z, w -> +z, d -> -z
            np.array([0.0, 1.0, 1.0]),
            np.array([0.0, 0.0, 1.0]),
            np.array([0.0, 0.0, -1.0]),
            # Surface
            np.array([0.0, 1.0, 1.0]),
            # Surface tangent
            np.array([0.0, 1.0, 0.0]),
        ),
    ],
)
def test_smoke_test(v, w, d, expected_surface, expected_tangent):
    R = 1
    rvw = np.array([np.zeros(3), v, w], dtype=np.float64)

    v_surface = surface_velocity(rvw, d, R)
    assert np.isclose(v_surface, expected_surface).all()

    v_tangent = tangent_surface_velocity(rvw, d, R)
    assert np.isclose(v_tangent, expected_tangent).all()
