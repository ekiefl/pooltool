"""make_kiss for circular cushion segments, whose nose is a tube around the nose circle."""

import numpy as np
import pytest

from pooltool import ptmath
from pooltool.constants import MIN_DIST, airborne, sliding, stationary
from pooltool.objects import Ball, BallParams, CircularCushionSegment
from pooltool.physics.resolve.ball_cushion import ball_ccushion_models
from pooltool.physics.resolve.models import BallCCushionModel

R = BallParams.default().R


def touch_distance(cushion: CircularCushionSegment) -> float:
    """Distance from the nose circle to the ball center at which the ball just touches."""
    return R + cushion.nose_radius


def expected_post_kiss_dist(cushion: CircularCushionSegment) -> float:
    return touch_distance(cushion) + MIN_DIST


def dist_to_nose_circle(ball: Ball, cushion: CircularCushionSegment) -> float:
    pos = ball.state.rvw[0]
    return ptmath.norm3d(pos - cushion.nearest_nose_point(pos))


def make_kiss_circular(ball: Ball, cushion: CircularCushionSegment) -> None:
    """Run make_kiss (arbitrarily uses Mathavan model)"""
    ball_ccushion_models[BallCCushionModel.MATHAVAN_2010]().make_kiss(ball, cushion)


def ball_at(
    cushion: CircularCushionSegment,
    polar_deg: float,
    penetrance: float = 0.0,
    vel: tuple[float, float, float] = (0.0, 0.0, 0.0),
    s: int = airborne,
) -> Ball:
    """Place a ball in the vertical plane through the axis and the +x direction.

    ``polar_deg`` is the angle of the ball center around the nose point, measured
    from the outward horizontal: 0 is level with the nose circle on the outer side, 90 is
    directly above it, 180 is level on the inner side. ``penetrance`` is how far
    inside the touch distance the center sits.
    """
    d = touch_distance(cushion) - penetrance
    polar = np.radians(polar_deg)
    nose_point = cushion.center + np.array([cushion.radius, 0.0, 0.0])
    normal = np.array([np.cos(polar), 0.0, np.sin(polar)])

    ball = Ball("cue")
    ball.state.rvw[0] = nose_point + d * normal
    ball.state.rvw[1] = vel
    ball.state.s = s

    assert dist_to_nose_circle(ball, cushion) == pytest.approx(d, abs=1e-12)

    return ball


def ball_on_table(
    cushion: CircularCushionSegment,
    penetrance: float = 0.0,
    vel: tuple[float, float, float] = (0.0, 0.0, 0.0),
    s: int = sliding,
) -> Ball:
    """Place a ball resting on the table (z = R) on the +x side of the cushion."""
    d = touch_distance(cushion) - penetrance
    horizontal = cushion.radius + np.sqrt(d**2 - (R - cushion.height) ** 2)

    ball = Ball("cue")
    ball.state.rvw[0] = (cushion.center[0] + horizontal, cushion.center[1], R)
    ball.state.rvw[1] = vel
    ball.state.s = s

    assert dist_to_nose_circle(ball, cushion) == pytest.approx(d, abs=1e-12)

    return ball


def assert_displaced_along(
    ball_before: Ball, ball: Ball, direction: np.ndarray
) -> None:
    displacement = ball.state.rvw[0] - ball_before.state.rvw[0]
    assert np.allclose(np.cross(displacement, direction), 0, atol=1e-10), (
        f"Expected displacement parallel to {direction}, got {displacement}"
    )


def test_ball_on_table(cushion_circular: CircularCushionSegment) -> None:
    """Ball resting on the table, slight overlap, sliding toward the jaw."""
    ball = ball_on_table(cushion_circular, penetrance=1e-7, vel=(-1.0, 0.0, 0.0))
    ball_before = ball.copy()

    make_kiss_circular(ball, cushion_circular)

    assert dist_to_nose_circle(ball, cushion_circular) == pytest.approx(
        expected_post_kiss_dist(cushion_circular), abs=1e-12
    )
    assert ball.state.rvw[0, 2] == R
    assert_displaced_along(ball_before, ball, ball_before.state.rvw[1])


def test_airborne_ball_on_outer_face(cushion_circular: CircularCushionSegment) -> None:
    ball = ball_at(
        cushion_circular, polar_deg=60, penetrance=1e-7, vel=(-0.5, 0.0, -1.0)
    )
    ball_before = ball.copy()

    make_kiss_circular(ball, cushion_circular)

    assert dist_to_nose_circle(ball, cushion_circular) == pytest.approx(
        expected_post_kiss_dist(cushion_circular), abs=1e-12
    )
    assert_displaced_along(ball_before, ball, ball_before.state.rvw[1])


def test_airborne_ball_on_inner_face(cushion_circular: CircularCushionSegment) -> None:
    """Dropping onto the lip from inside the ring: the normal points toward the axis."""
    ball = ball_at(
        cushion_circular, polar_deg=100, penetrance=1e-7, vel=(0.2, 0.0, -1.0)
    )
    ball_before = ball.copy()
    assert np.hypot(*ball.state.rvw[0, :2]) < cushion_circular.radius

    make_kiss_circular(ball, cushion_circular)

    assert dist_to_nose_circle(ball, cushion_circular) == pytest.approx(
        expected_post_kiss_dist(cushion_circular), abs=1e-12
    )
    assert_displaced_along(ball_before, ball, ball_before.state.rvw[1])


def test_stationary_ball_on_table_falls_back(
    cushion_circular: CircularCushionSegment,
) -> None:
    ball = ball_on_table(cushion_circular, penetrance=1e-7, s=stationary)

    make_kiss_circular(ball, cushion_circular)

    assert dist_to_nose_circle(ball, cushion_circular) == pytest.approx(
        expected_post_kiss_dist(cushion_circular), abs=1e-12
    )
    assert ball.state.rvw[0, 2] == R


def test_airborne_tangential_velocity_falls_back_along_normal(
    cushion_circular: CircularCushionSegment,
) -> None:
    """Velocity tangent to the surface cannot be traced back; place along the normal."""
    ball = ball_at(cushion_circular, polar_deg=60, penetrance=1e-7, vel=(0.0, 2.0, 0.0))
    ball_before = ball.copy()
    normal = cushion_circular.get_normal_3d(ball_before.state.rvw[0])

    make_kiss_circular(ball, cushion_circular)

    assert dist_to_nose_circle(ball, cushion_circular) == pytest.approx(
        expected_post_kiss_dist(cushion_circular), abs=1e-12
    )
    assert_displaced_along(ball_before, ball, normal)


def test_airborne_ball_rewound_below_table_is_placed_on_table(
    cushion_circular: CircularCushionSegment,
) -> None:
    """Rising into the underside of the nose from table height lands on the table."""
    polar_deg = np.degrees(
        np.arcsin(
            (R + 1e-7 - cushion_circular.height) / touch_distance(cushion_circular)
        )
    )
    ball = ball_at(
        cushion_circular, polar_deg=polar_deg, penetrance=1e-7, vel=(0.0, 0.0, 1.0)
    )
    assert ball.state.rvw[0, 2] > R

    make_kiss_circular(ball, cushion_circular)

    assert ball.state.rvw[0, 2] == R
    assert dist_to_nose_circle(ball, cushion_circular) == pytest.approx(
        expected_post_kiss_dist(cushion_circular), abs=1e-12
    )
