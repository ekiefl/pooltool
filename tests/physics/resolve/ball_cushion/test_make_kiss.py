import numpy as np
import pytest

from pooltool import ptmath
from pooltool.constants import MIN_DIST, airborne, sliding, stationary
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


def ball_at_3d_dist(
    cushion: LinearCushionSegment,
    theta_deg: float,
    penetrance: float = 0.0,
    vel: tuple[float, float, float] = (0.0, 0.0, 0.0),
    s: int = sliding,
) -> Ball:
    """Place a ball in polar coordinates around the cushion line (xz-plane).

    The ball is on the -x side of the cushion. Theta is the elevation angle of
    the line from the cushion axis to the ball center, measured in the xz-plane
    from horizontal:

        theta_deg = 0   → ball at cushion height (horizontal -x direction)
        theta_deg = +90 → ball directly above cushion (+z)
        theta_deg = -90 → ball directly below cushion (-z)

    Args:
        theta_deg: Elevation angle of the ball position from the cushion axis (degrees).
        penetrance: Effective dr inside the touch radius. ``penetrance = 0`` puts the
            ball center at distance R from the cushion axis (just touching).
            Positive values place the ball overlapping the cushion; negative values
            place it separated.

    Assumes the cushion is along the y-axis (as in the conftest fixture).
    """
    R = BallParams.default().R
    h_cushion = cushion.p1[2]
    r = R - penetrance
    theta_rad = np.radians(theta_deg)
    xb = -r * np.cos(theta_rad)
    zb = h_cushion + r * np.sin(theta_rad)

    ball = Ball("cue")
    ball.state.rvw[0] = (xb, 0, zb)
    ball.state.rvw[1] = vel
    ball.state.s = s

    assert dist_to_cushion_axis(ball, cushion) == pytest.approx(r, abs=1e-12)

    return ball


def ball_on_table(
    cushion: LinearCushionSegment,
    penetrance: float = 0.0,
    vel: tuple[float, float, float] = (0.0, 0.0, 0.0),
    s: int = sliding,
) -> Ball:
    """Place a ball resting on the table (z = R) at a given 3D distance from the cushion axis.

    Convenient specialization of :func:`ball_at_3d_dist` for the common scenario where
    the cushion height exceeds R (so the on-table elevation angle is awkward to express
    in polar form).

    Args:
        penetrance: Effective dr inside the touch radius. ``penetrance = 0`` puts the
            ball center at distance R from the cushion axis (just touching).
            Positive values place the ball overlapping the cushion; negative values
            place it separated.

    The ball is placed on the -x side, at y = 0. Assumes the cushion is along the
    y-axis (as in the conftest fixture).
    """
    R = BallParams.default().R
    h_cushion = cushion.p1[2]
    r = R - penetrance
    xy_dist = float(np.sqrt(r**2 - (R - h_cushion) ** 2))

    ball = Ball("cue")
    ball.state.rvw[0] = (-xy_dist, 0, R)
    ball.state.rvw[1] = vel
    ball.state.s = s

    assert ball.state.rvw[0, 2] == R
    assert dist_to_cushion_axis(ball, cushion) == pytest.approx(r, abs=1e-12)

    return ball


def xy_dist_to_cushion_axis(ball: Ball, cushion: LinearCushionSegment) -> float:
    """XY-distance from ball center to the cushion axis (line through p1, p2)."""
    pos = ball.state.rvw[0]
    c = ptmath.point_on_line_closest_to_point(cushion.p1, cushion.p2, pos)
    c[2] = pos[2]
    return ptmath.norm3d(pos - c)


def dist_to_cushion_axis(ball: Ball, cushion: LinearCushionSegment) -> float:
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


# -----------------------
# 3D linear behavior: cushion is a 1D line at z = cushion_height. "Touch" means
# the ball center is at 3D distance R from that line, not just R in xy.


def test_3d_ball_on_table(cushion: LinearCushionSegment) -> None:
    """Ball resting on the table (z=R), slight overlap, horizontal velocity."""
    R = BallParams.default().R
    ball = ball_on_table(cushion, penetrance=1e-7, vel=(1.0, 0.0, 0.0))
    ball_before = ball.copy()

    make_kiss_linear(ball, cushion)

    assert dist_to_cushion_axis(ball, cushion) == pytest.approx(
        R + MIN_DIST, abs=1e-12
    )
    assert_displaced_along_velocity(ball_before, ball)


def test_3d_ball_above_cushion(cushion: LinearCushionSegment) -> None:
    """Ball above cushion line, slight overlap, horizontal velocity."""
    R = BallParams.default().R
    ball = ball_at_3d_dist(cushion, theta_deg=15, penetrance=1e-7, vel=(1.0, 0.0, 0.0))
    ball_before = ball.copy()

    make_kiss_linear(ball, cushion)

    assert dist_to_cushion_axis(ball, cushion) == pytest.approx(
        R + MIN_DIST, abs=1e-12
    )
    assert_displaced_along_velocity(ball_before, ball)


def test_3d_ball_above_cushion_diagonal_velocity(cushion: LinearCushionSegment) -> None:
    """Ball above cushion line with vz != 0; displacement still along 3D velocity."""
    R = BallParams.default().R
    vel_unit = np.array([1.0, 0.0, -0.5]) / np.linalg.norm([1.0, 0.0, -0.5])
    vel = (float(vel_unit[0]), float(vel_unit[1]), float(vel_unit[2]))
    ball = ball_at_3d_dist(cushion, theta_deg=15, penetrance=1e-7, vel=vel)
    ball_before = ball.copy()

    make_kiss_linear(ball, cushion)

    assert dist_to_cushion_axis(ball, cushion) == pytest.approx(
        R + MIN_DIST, abs=1e-12
    )
    assert_displaced_along_velocity(ball_before, ball)


@pytest.mark.parametrize(
    "ball_factory",
    [
        pytest.param(
            lambda c: ball_on_table(c, penetrance=1e-7, s=stationary),
            id="stationary_fallback",
        ),
        pytest.param(
            lambda c: ball_on_table(c, penetrance=1e-7, vel=(1.0, 0.0, 0.0)),
            id="sliding_horizontal_velocity",
        ),
        pytest.param(
            lambda c: ball_on_table(c, penetrance=1e-7, vel=(0.1, 1.0, 0.0)),
            id="sliding_grazing_fallback",
        ),
        pytest.param(
            lambda c: ball_on_table(
                c, penetrance=1e-7, vel=(1.0, 0.0, 0.5), s=airborne
            ),
            id="airborne_bouncing_up",
        ),
    ],
)
def test_3d_ball_on_table_stays_on_table(
    cushion: LinearCushionSegment,
    ball_factory,
) -> None:
    """After make_kiss, an on-table ball (z=R) must not penetrate the table.

    Covers both branches (velocity and fallback) and motion states (stationary,
    sliding, airborne with upward vz from a table bounce).
    """
    R = BallParams.default().R
    ball = ball_factory(cushion)

    make_kiss_linear(ball, cushion)

    assert ball.state.rvw[0, 2] >= R - 1e-12, (
        f"Ball penetrated the table: z={ball.state.rvw[0, 2]}, R={R}"
    )
    assert dist_to_cushion_axis(ball, cushion) == pytest.approx(
        R + MIN_DIST, abs=1e-12
    )
