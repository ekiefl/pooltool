import numpy as np
import pytest

import pooltool.constants as const
from pooltool.physics.utils import (
    final_ball_motion_state,
    get_airborne_time,
    surface_velocity,
    tangent_surface_velocity,
)


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


@pytest.mark.parametrize(
    "rvw,R,g,expected",
    [
        # Zero gravity: no return to table.
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
            0.0,
            np.inf,
        ),
        # Drop from apex (v_z = 0): t = sqrt(2 * (z - R) / g).
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
        # xy-velocity does not affect time-to-table.
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
        # Ball at z=R with downward velocity: already touching, t = 0.
        (
            np.array(
                [
                    [0.0, 0.0, 0.1],
                    [0.0, -1.0, 0.0],
                    [0.0, 0.0, 0.0],
                ],
                dtype=np.float64,
            ),
            0.1,
            10.0,
            0.0,
        ),
    ],
)
def test_get_airborne_time(rvw, R, g, expected):
    assert np.isclose(get_airborne_time(rvw, R, g), expected)


R_BALL = 0.028575


def _rvw(z: float, v: tuple, w: tuple) -> np.ndarray:
    return np.array([[0.0, 0.0, z], v, w], dtype=np.float64)


@pytest.mark.parametrize(
    "rvw, expected",
    [
        (_rvw(-0.1, (0, 0, 0), (0, 0, 0)), const.pocketed),
        (_rvw(R_BALL, (1, 0, 0.5), (0, 0, 0)), const.airborne),
        (_rvw(R_BALL, (0, 0, -0.5), (0, 0, 0)), const.airborne),
        (_rvw(2 * R_BALL, (0, 0, 0), (0, 0, 0)), const.airborne),
        (_rvw(R_BALL, (1, 0, 0), (0, 0, 0)), const.sliding),
        (_rvw(R_BALL, (0, 0, 0), (0, 5, 0)), const.sliding),
        (_rvw(R_BALL, (1, 0, 0), (0, 1 / R_BALL, 0)), const.rolling),
        (_rvw(R_BALL, (1, 0, 0), (0, 1 / R_BALL, 3)), const.rolling),
        (_rvw(R_BALL, (0, 0, 0), (0, 0, 3)), const.spinning),
        (_rvw(R_BALL, (0, 0, 0), (0, 0, 0)), const.stationary),
        (_rvw(R_BALL, (const.EPS / 2, 0, 0), (0, 0, const.EPS / 2)), const.stationary),
    ],
    ids=[
        "below table is pocketed",
        "upward velocity is airborne",
        "downward velocity is airborne",
        "above the table is airborne",
        "translation without rotation slides",
        "rotation without translation slides",
        "matched rotation rolls",
        "matched rotation with vertical spin rolls",
        "vertical spin alone spins",
        "no motion is stationary",
        "sub-EPS motion is stationary",
    ],
)
def test_final_ball_motion_state(rvw, expected):
    assert final_ball_motion_state(rvw, R_BALL) == expected
