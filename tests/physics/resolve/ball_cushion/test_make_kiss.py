import numpy as np
import pytest

from pooltool import ptmath
from pooltool.constants import MIN_DIST, sliding, stationary
from pooltool.objects import (
    Ball,
    BallParams,
    CircularCushionSegment,
    LinearCushionSegment,
)
from pooltool.physics.resolve.ball_cushion import (
    ball_ccushion_models,
    ball_lcushion_models,
)
from pooltool.physics.resolve.ball_cushion.core import FALLBACK_DISPLACEMENT_FACTOR
from pooltool.physics.resolve.models import BallCCushionModel, BallLCushionModel

GRAZING_THRESHOLD_INCIDENCE_DEG = float(
    np.degrees(np.arccos(1.0 / FALLBACK_DISPLACEMENT_FACTOR))
)
"""Incidence angle (from cushion normal, degrees) above which make_kiss falls back.

Derived from FALLBACK_DISPLACEMENT_FACTOR: the velocity-based displacement is
``spacer / cos(incidence)``, so fallback triggers when
``cos(incidence) < 1 / FALLBACK_DISPLACEMENT_FACTOR``.
"""


def ball_at(
    pos: tuple[float, float, float],
    vel: tuple[float, float, float] = (0.0, 0.0, 0.0),
    s: int = sliding,
) -> Ball:
    """Create a Ball with given position, velocity, and motion state."""
    ball = Ball("cue")
    ball.state.rvw[0] = pos
    ball.state.rvw[1] = vel
    ball.state.s = s
    return ball


def xy_dist_to_cushion_axis(ball: Ball, cushion: LinearCushionSegment) -> float:
    """XY-distance from ball center to the cushion axis (line through p1, p2)."""
    pos = ball.state.rvw[0]
    c = ptmath.point_on_line_closest_to_point(cushion.p1, cushion.p2, pos)
    c[2] = pos[2]
    return ptmath.norm3d(pos - c)


def xyz_dist_to_cushion_axis(ball: Ball, cushion: LinearCushionSegment) -> float:
    """3D-distance from ball center to the cushion axis (line through p1, p2)."""
    pos = ball.state.rvw[0]
    c = ptmath.point_on_line_closest_to_point(cushion.p1, cushion.p2, pos)
    return ptmath.norm3d(pos - c)


def xy_dist_to_cushion_center(ball: Ball, cushion: CircularCushionSegment) -> float:
    """XY-distance from ball center to the cushion center."""
    pos = ball.state.rvw[0]
    c = np.array([cushion.center[0], cushion.center[1], pos[2]])
    return ptmath.norm3d(pos - c)


def make_kiss_linear(ball: Ball, cushion: LinearCushionSegment) -> None:
    """Run make_kiss (arbitrarily uses Mathavan model)"""
    ball_lcushion_models[BallLCushionModel.MATHAVAN_2010]().make_kiss(ball, cushion)


def make_kiss_circular(ball: Ball, cushion: CircularCushionSegment) -> None:
    """Run make_kiss (arbitrarily uses Mathavan model)"""
    ball_ccushion_models[BallCCushionModel.MATHAVAN_2010]().make_kiss(ball, cushion)


def assert_displaced_along_velocity(ball_before: Ball, ball: Ball) -> None:
    """Assert ball's displacement is parallel to its pre-kiss velocity."""
    displacement = ball.state.rvw[0] - ball_before.state.rvw[0]
    vel = ball_before.state.rvw[1]
    cross = np.cross(displacement, vel)
    assert np.allclose(cross, 0, atol=1e-10), (
        f"Expected displacement parallel to velocity, "
        f"got displacement={displacement}, vel={vel}"
    )


def assert_displaced_along_normal(
    ball_before: Ball,
    ball: Ball,
    cushion: LinearCushionSegment | CircularCushionSegment,
) -> None:
    """Assert ball's displacement is along the cushion normal."""
    displacement = ball.state.rvw[0] - ball_before.state.rvw[0]
    normal = cushion.get_normal_xy(ball.state.rvw[0])
    disp_norm = displacement / np.linalg.norm(displacement)
    assert np.allclose(np.abs(np.dot(disp_norm, normal)), 1.0, atol=1e-10), (
        f"Expected displacement along normal, "
        f"got displacement={displacement}, normal={normal}"
    )


# -----------------------


@pytest.mark.parametrize(
    "incidence_angle_deg",
    [
        65,
        70,
        75,
        GRAZING_THRESHOLD_INCIDENCE_DEG - 0.001,
    ],
)
def test_velocity_branch(
    cushion: LinearCushionSegment,
    incidence_angle_deg: float,
) -> None:
    """Below the grazing threshold, displacement is aligned with velocity."""
    R = BallParams.default().R
    rads = np.radians(incidence_angle_deg)
    vel = (np.cos(rads), np.sin(rads), 0.0)
    ball = ball_at((-R, 0, R), vel)
    ball_before = ball.copy()

    make_kiss_linear(ball, cushion)

    assert xy_dist_to_cushion_axis(ball, cushion) == pytest.approx(
        R + MIN_DIST, abs=1e-12
    )
    assert_displaced_along_velocity(ball_before, ball)


@pytest.mark.parametrize(
    "incidence_angle_deg",
    [
        65,
        70,
        75,
        GRAZING_THRESHOLD_INCIDENCE_DEG - 0.05,
    ],
)
def test_velocity_branch_circular(
    cushion_circular: CircularCushionSegment,
    incidence_angle_deg: float,
) -> None:
    """Below the grazing threshold, displacement is aligned with velocity."""
    R = BallParams.default().R
    dist = R + cushion_circular.radius
    rads = np.radians(incidence_angle_deg)
    vel = (-np.cos(rads), np.sin(rads), 0.0)
    ball = ball_at((dist, 0, R), vel)
    ball_before = ball.copy()

    make_kiss_circular(ball, cushion_circular)

    assert xy_dist_to_cushion_center(ball, cushion_circular) == pytest.approx(
        dist + MIN_DIST, abs=1e-12
    )
    assert_displaced_along_velocity(ball_before, ball)


@pytest.mark.parametrize(
    "incidence_angle_deg",
    [
        GRAZING_THRESHOLD_INCIDENCE_DEG + 0.001,
        80,
        85,
        89,
    ],
)
def test_fallback_branch(
    cushion: LinearCushionSegment,
    incidence_angle_deg: float,
) -> None:
    """Above the grazing threshold, displacement is aligned with the cushion normal."""
    R = BallParams.default().R
    rads = np.radians(incidence_angle_deg)
    vel = (np.cos(rads), np.sin(rads), 0.0)
    ball = ball_at((-R, 0, R), vel)
    ball_before = ball.copy()

    make_kiss_linear(ball, cushion)

    assert xy_dist_to_cushion_axis(ball, cushion) == pytest.approx(
        R + MIN_DIST, abs=1e-12
    )
    assert_displaced_along_normal(ball_before, ball, cushion)


@pytest.mark.parametrize(
    "incidence_angle_deg",
    [
        GRAZING_THRESHOLD_INCIDENCE_DEG + 0.05,
        80,
        85,
        89,
    ],
)
def test_fallback_branch_circular(
    cushion_circular: CircularCushionSegment,
    incidence_angle_deg: float,
) -> None:
    """Above the grazing threshold, displacement is aligned with the cushion normal."""
    R = BallParams.default().R
    dist = R + cushion_circular.radius
    rads = np.radians(incidence_angle_deg)
    vel = (-np.cos(rads), np.sin(rads), 0.0)
    ball = ball_at((dist, 0, R), vel)
    ball_before = ball.copy()

    make_kiss_circular(ball, cushion_circular)

    assert xy_dist_to_cushion_center(ball, cushion_circular) == pytest.approx(
        dist + MIN_DIST, abs=1e-12
    )
    assert_displaced_along_normal(ball_before, ball, cushion_circular)


@pytest.mark.parametrize("offset", [-1e-7, 0, 1e-7])
def test_head_on_lands_at_promised_separation(
    cushion: LinearCushionSegment, offset: float
) -> None:
    """Head-on approach lands at exactly R + MIN_DIST regardless of small initial offset."""
    R = BallParams.default().R
    ball = ball_at((-(R + offset), 0, R), (1.0, 0.0, 0.0))

    make_kiss_linear(ball, cushion)

    assert ball.state.rvw[0, 0] == pytest.approx(-(R + MIN_DIST), abs=1e-12)
    assert xy_dist_to_cushion_axis(ball, cushion) == pytest.approx(
        R + MIN_DIST, abs=1e-12
    )


@pytest.mark.parametrize("offset", [-1e-7, 0, 1e-7])
def test_head_on_lands_at_promised_separation_circular(
    cushion_circular: CircularCushionSegment, offset: float
) -> None:
    """Head-on approach lands at exactly R + r + MIN_DIST from cushion center, regardless of small initial offset."""
    R = BallParams.default().R
    target = R + cushion_circular.radius + MIN_DIST
    ball = ball_at((target + offset, 0, R), (-1.0, 0.0, 0.0))

    make_kiss_circular(ball, cushion_circular)

    assert ball.state.rvw[0, 0] == pytest.approx(target, abs=1e-12)
    assert xy_dist_to_cushion_center(ball, cushion_circular) == pytest.approx(
        target, abs=1e-12
    )


def test_stationary_overlapping_uses_fallback(
    cushion: LinearCushionSegment,
) -> None:
    """A stationary, slightly-overlapping ball is pushed along the normal to R + MIN_DIST."""
    R = BallParams.default().R
    ball = ball_at((-(R - 1e-7), 0, R), s=stationary)
    ball_before = ball.copy()

    make_kiss_linear(ball, cushion)

    assert xy_dist_to_cushion_axis(ball, cushion) == pytest.approx(
        R + MIN_DIST, abs=1e-12
    )
    assert_displaced_along_normal(ball_before, ball, cushion)


# -----------------------


def test_stationary_overlapping_uses_fallback_circular(
    cushion_circular: CircularCushionSegment,
) -> None:
    """A stationary, slightly-overlapping ball is pushed along the normal to the target separation."""
    R = BallParams.default().R
    target = R + cushion_circular.radius + MIN_DIST
    ball = ball_at((target - 1e-7, 0, R), s=stationary)
    ball_before = ball.copy()

    make_kiss_circular(ball, cushion_circular)

    assert xy_dist_to_cushion_center(ball, cushion_circular) == pytest.approx(
        target, abs=1e-12
    )
    assert_displaced_along_normal(ball_before, ball, cushion_circular)
