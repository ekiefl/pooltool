import numpy as np
import pytest

from pooltool import ptmath
from pooltool.constants import MIN_DIST, airborne, rolling, sliding, stationary
from pooltool.objects import (
    Ball,
    BallParams,
    LinearCushionSegment,
)
from pooltool.physics.resolve.ball_cushion import (
    ball_lcushion_models,
)
from pooltool.physics.resolve.models import BallLCushionModel


def ball_at(
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
    """Place a ball resting on the table (z = R) at a given distance from the cushion axis.

    Convenient specialization of :func:`ball_at` for the common scenario where
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


def dist_to_cushion_axis(ball: Ball, cushion: LinearCushionSegment) -> float:
    """Distance from ball center to the cushion axis (line through p1, p2)."""
    pos = ball.state.rvw[0]
    c = ptmath.point_on_line_closest_to_point(cushion.p1, cushion.p2, pos)
    return ptmath.norm3d(pos - c)


def make_kiss_linear(ball: Ball, cushion: LinearCushionSegment) -> None:
    """Run make_kiss (arbitrarily uses Mathavan model)"""
    ball_lcushion_models[BallLCushionModel.MATHAVAN_2010]().make_kiss(ball, cushion)


def assert_displaced_along_velocity(ball_before: Ball, ball: Ball) -> None:
    """Assert ball's displacement is parallel to its pre-kiss velocity."""
    displacement = ball.state.rvw[0] - ball_before.state.rvw[0]
    vel = ball_before.state.rvw[1]
    cross = np.cross(displacement, vel)
    assert np.allclose(cross, 0, atol=1e-10), (
        f"Expected displacement parallel to velocity, "
        f"got displacement={displacement}, vel={vel}"
    )


def test_ball_on_table(cushion: LinearCushionSegment) -> None:
    """Ball resting on the table (z=R), slight overlap, horizontal velocity."""
    R = BallParams.default().R
    ball = ball_on_table(cushion, penetrance=1e-7, vel=(1.0, 0.0, 0.0))
    ball_before = ball.copy()

    make_kiss_linear(ball, cushion)

    assert dist_to_cushion_axis(ball, cushion) == pytest.approx(R + MIN_DIST, abs=1e-12)
    assert_displaced_along_velocity(ball_before, ball)


def test_ball_above_cushion(cushion: LinearCushionSegment) -> None:
    """Airborne ball above cushion line, slight overlap, horizontal velocity."""
    R = BallParams.default().R
    ball = ball_at(
        cushion, theta_deg=15, penetrance=1e-7, vel=(1.0, 0.0, 0.0), s=airborne
    )
    ball_before = ball.copy()

    make_kiss_linear(ball, cushion)

    assert dist_to_cushion_axis(ball, cushion) == pytest.approx(R + MIN_DIST, abs=1e-12)
    assert_displaced_along_velocity(ball_before, ball)


def test_ball_above_cushion_diagonal_velocity(cushion: LinearCushionSegment) -> None:
    """Airborne ball above cushion with vz != 0; displacement still along 3D velocity."""
    R = BallParams.default().R
    vel_unit = np.array([1.0, 0.0, -0.5]) / np.linalg.norm([1.0, 0.0, -0.5])
    vel = (float(vel_unit[0]), float(vel_unit[1]), float(vel_unit[2]))
    ball = ball_at(cushion, theta_deg=15, penetrance=1e-7, vel=vel, s=airborne)
    ball_before = ball.copy()

    make_kiss_linear(ball, cushion)

    assert dist_to_cushion_axis(ball, cushion) == pytest.approx(R + MIN_DIST, abs=1e-12)
    assert_displaced_along_velocity(ball_before, ball)


@pytest.mark.parametrize(
    "ball_factory",
    [
        pytest.param(
            lambda c: ball_on_table(c, penetrance=-0.005, s=stationary),
            id="stationary_fallback_lift",
        ),
        pytest.param(
            lambda c: ball_on_table(c, penetrance=1e-7, vel=(1.0, 0.0, 0.0)),
            id="sliding_horizontal_velocity",
        ),
        pytest.param(
            lambda c: ball_on_table(c, penetrance=-0.005, vel=(0.01, 1.0, 0.0)),
            id="sliding_grazing_fallback_lift",
        ),
    ],
)
def test_nonairborne_ball_on_table_stays_on_table(
    cushion: LinearCushionSegment,
    ball_factory,
) -> None:
    """After make_kiss, a non-airborne ball must rest exactly on the table (z == R).

    Negative penetrance places the ball center beyond the touch radius, so the
    fallback projects it toward the cushion line (which sits above the table).
    The projected position lifts above R; the table constraint must rotate the
    ball back down to z = R without changing its distance to the cushion line.
    """
    R = BallParams.default().R
    ball = ball_factory(cushion)

    make_kiss_linear(ball, cushion)

    assert ball.state.rvw[0, 2] == pytest.approx(R, abs=1e-12), (
        f"Non-airborne ball not on table: z={ball.state.rvw[0, 2]}, R={R}"
    )
    assert dist_to_cushion_axis(ball, cushion) == pytest.approx(R + MIN_DIST, abs=1e-12)


def test_airborne_overlapping_ball_on_table_lands_on_table(
    cushion: LinearCushionSegment,
) -> None:
    """Airborne overlapping ball at z=R with upward vz ends up exactly at z=R.

    With positive penetrance, make_kiss moves backward along v (t < 0). vz > 0 means
    the quadratic-solved z drops below R, so the ``airborne and z >= R`` short-circuit
    in ``_constrain_to_table`` does not apply — the rotation pins z to R exactly.
    """
    R = BallParams.default().R
    ball = ball_on_table(cushion, penetrance=1e-7, vel=(1.0, 0.0, 0.5), s=airborne)

    make_kiss_linear(ball, cushion)

    assert ball.state.rvw[0, 2] == pytest.approx(R, abs=1e-12), (
        f"Airborne ball not on table: z={ball.state.rvw[0, 2]}, R={R}"
    )
    assert dist_to_cushion_axis(ball, cushion) == pytest.approx(R + MIN_DIST, abs=1e-12)


def test_airborne_stress(cushion: LinearCushionSegment) -> None:
    """Random airborne configurations all satisfy dist == R + spacer after make_kiss.

    Sweeps theta, penetrance, and 3D velocity. Covers both branches: the velocity
    branch (most cases) and the fallback (grazing or velocity-parallel-to-axis).
    """
    R = BallParams.default().R
    rng = np.random.default_rng(42)
    N = 50

    for _ in range(N):
        theta_deg = float(rng.uniform(-85.0, 85.0))
        penetrance = float(rng.uniform(-0.01, 0.005))
        vel_dir = rng.standard_normal(3)
        vel_dir /= np.linalg.norm(vel_dir)
        speed = float(rng.uniform(0.1, 2.0))
        vel = (
            float(speed * vel_dir[0]),
            float(speed * vel_dir[1]),
            float(speed * vel_dir[2]),
        )

        ball = ball_at(cushion, theta_deg, penetrance, vel=vel, s=airborne)
        make_kiss_linear(ball, cushion)

        assert dist_to_cushion_axis(ball, cushion) == pytest.approx(
            R + MIN_DIST, abs=1e-12
        ), (
            f"airborne case failed: theta_deg={theta_deg}, penetrance={penetrance}, "
            f"vel={vel}"
        )


def test_nonairborne_stress(cushion: LinearCushionSegment) -> None:
    """Random sliding/rolling configurations all satisfy dist == R + spacer after make_kiss.

    Sweeps penetrance, xy velocity, and motion state (sliding vs rolling).
    """
    R = BallParams.default().R
    rng = np.random.default_rng(42)
    states = (sliding, rolling)
    N = 50

    for _ in range(N):
        penetrance = float(rng.uniform(-0.01, 0.005))
        vel_xy = rng.standard_normal(2)
        vel_xy /= np.linalg.norm(vel_xy)
        speed = float(rng.uniform(0.1, 2.0))
        vel = (float(speed * vel_xy[0]), float(speed * vel_xy[1]), 0.0)
        state = states[int(rng.integers(0, 2))]

        ball = ball_on_table(cushion, penetrance=penetrance, vel=vel, s=state)
        make_kiss_linear(ball, cushion)

        assert dist_to_cushion_axis(ball, cushion) == pytest.approx(
            R + MIN_DIST, abs=1e-12
        ), (
            f"non-airborne case failed: penetrance={penetrance}, vel={vel}, state={state}"
        )
