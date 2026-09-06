import numpy as np
import pytest

from pooltool import ptmath
from pooltool.constants import MIN_DIST, airborne, rolling, sliding, stationary
from pooltool.objects import Ball, BallParams
from pooltool.physics.resolve.ball_ball.frictional_inelastic import (
    FrictionalInelastic3D,
)

R = BallParams.default().R
TARGET = 2 * R + MIN_DIST
Z_HAT = np.array([0.0, 0.0, 1.0])
MODEL = FrictionalInelastic3D()


def make_ball(
    pos: tuple[float, float, float],
    vel: tuple[float, float, float] = (0.0, 0.0, 0.0),
    s: int = stationary,
) -> Ball:
    ball = Ball("cue")
    ball.state.rvw[0] = pos
    ball.state.rvw[1] = vel
    ball.state.s = s
    return ball


def resting_ball() -> Ball:
    """A stationary ball resting on the table at the origin."""
    return make_ball((0.0, 0.0, R))


def ball_offset_from(
    other: Ball,
    direction: tuple[float, float, float],
    penetrance: float,
    vel: tuple[float, float, float] = (0.0, 0.0, 0.0),
    s: int = sliding,
) -> Ball:
    """Place a ball at distance ``2R - penetrance`` from ``other`` along ``direction``.

    Args:
        penetrance: Positive values overlap the balls; negative values separate them.
    """
    unit = np.array(direction, dtype=np.float64)
    unit /= np.linalg.norm(unit)
    pos = other.state.rvw[0] + (2 * R - penetrance) * unit
    return make_ball((float(pos[0]), float(pos[1]), float(pos[2])), vel, s)


def separation(ball1: Ball, ball2: Ball) -> float:
    return ptmath.norm3d(ball1.state.rvw[0] - ball2.state.rvw[0])


def assert_kissing(ball1: Ball, ball2: Ball) -> None:
    assert separation(ball1, ball2) == pytest.approx(TARGET, abs=1e-12)


def assert_on_table(ball: Ball) -> None:
    assert ball.state.rvw[0, 2] == pytest.approx(R, abs=1e-12)


def assert_displaced_along_velocity(before: Ball, after: Ball) -> None:
    displacement = after.state.rvw[0] - before.state.rvw[0]
    cross = np.cross(displacement, before.state.rvw[1])
    assert np.allclose(cross, 0, atol=1e-10)


def assert_displaced_within_velocity_plane(before: Ball, after: Ball) -> None:
    """The net displacement lies in the vertical plane containing the velocity."""
    horizontal = before.state.rvw[1] * np.array([1.0, 1.0, 0.0])
    normal = np.cross(horizontal / np.linalg.norm(horizontal), Z_HAT)
    displacement = after.state.rvw[0] - before.state.rvw[0]
    assert np.dot(displacement, normal) == pytest.approx(0.0, abs=1e-12)


def test_on_table_head_on() -> None:
    """Two on-table balls: the mover is rewound along its velocity, the rester stays put."""
    ob = resting_ball()
    cb = ball_offset_from(ob, (-1, 0, 0), penetrance=1e-7, vel=(1.0, 0.0, 0.0))
    cb_before, ob_before = cb.copy(), ob.copy()

    MODEL.make_kiss(cb, ob)

    assert_kissing(cb, ob)
    assert_on_table(cb)
    assert np.array_equal(ob.state.rvw[0], ob_before.state.rvw[0])
    assert_displaced_along_velocity(cb_before, cb)


def test_airborne_descending_onto_resting_ball() -> None:
    """A descending airborne ball is rewound up its own line; nothing needs lifting."""
    ob = resting_ball()
    cb = ball_offset_from(
        ob, (-1, 0, 1), penetrance=1e-7, vel=(2.0, 0.0, -2.0), s=airborne
    )
    cb_before, ob_before = cb.copy(), ob.copy()

    MODEL.make_kiss(cb, ob)

    assert_kissing(cb, ob)
    assert cb.state.rvw[0, 2] > R
    assert np.array_equal(ob.state.rvw[0], ob_before.state.rvw[0])
    assert_displaced_along_velocity(cb_before, cb)


@pytest.mark.parametrize(
    "vel",
    [
        pytest.param((1.0, 0.0, 0.5), id="velocity_in_plane_of_centers"),
        pytest.param((0.3, 1.0, 1.0), id="velocity_off_plane_of_centers"),
    ],
)
def test_launching_ball_rewound_below_table_is_lifted(
    vel: tuple[float, float, float],
) -> None:
    """A just-launched ball is rewound downward, then lifted within its own velocity plane.

    The rewind follows the velocity, and the lift slides along the sphere in the
    vertical plane of that same velocity, so the net displacement from the original
    position lies in that plane.
    """
    ob = resting_ball()
    cb = ball_offset_from(ob, (-1, 0, 0), penetrance=1e-7, vel=vel, s=airborne)
    cb_before, ob_before = cb.copy(), ob.copy()

    MODEL.make_kiss(cb, ob)

    assert_kissing(cb, ob)
    assert_on_table(cb)
    assert np.array_equal(ob.state.rvw[0], ob_before.state.rvw[0])
    assert_displaced_within_velocity_plane(cb_before, cb)


@pytest.mark.parametrize(
    "penetrance",
    [
        pytest.param(2e-5, id="overlapping_resting_ball_pushed_into_table"),
        pytest.param(-2e-5, id="separated_resting_ball_lifted_off_table"),
    ],
)
def test_fallback_restores_resting_ball_to_table(penetrance: float) -> None:
    """The fallback pushes along a tilted line of centers; the resting ball is put back.

    A displacement of 2e-5 shifts the midpoint by more than 5x the spacer, which
    triggers the fallback. That moves the resting ball off the table along the tilted
    line of centers, and the lift must return it to exactly z == R without changing the
    separation.
    """
    ob = resting_ball()
    cb = ball_offset_from(
        ob, (-1, 0, 1), penetrance=penetrance, vel=(2.0, 0.0, -2.0), s=airborne
    )

    MODEL.make_kiss(cb, ob)

    assert_kissing(cb, ob)
    assert_on_table(ob)
    assert cb.state.rvw[0, 2] >= R


def test_both_stationary_overlapping() -> None:
    """Two resting balls with no velocity are split symmetrically along the line of centers."""
    ob = resting_ball()
    cb = ball_offset_from(ob, (-1, 0, 0), penetrance=1e-7, s=stationary)
    midpoint_before = (cb.state.rvw[0] + ob.state.rvw[0]) / 2

    MODEL.make_kiss(cb, ob)

    midpoint_after = (cb.state.rvw[0] + ob.state.rvw[0]) / 2
    assert_kissing(cb, ob)
    assert_on_table(cb)
    assert_on_table(ob)
    assert np.allclose(midpoint_before, midpoint_after, atol=1e-12)


def test_grazing_separated_balls_fall_back() -> None:
    """A ball sliding tangentially past a slightly separated ball still gets a valid position.

    With the relative velocity nearly perpendicular to the line of centers, the
    quadratic has no real root. make_kiss must fall back to the line of centers rather
    than propagate an empty root set.
    """
    ob = resting_ball()
    cb = ball_offset_from(ob, (-1, 0, 0), penetrance=-3e-6, vel=(0.001, 1.0, 0.0))

    MODEL.make_kiss(cb, ob)

    assert np.all(np.isfinite(cb.state.rvw[0]))
    assert_kissing(cb, ob)
    assert_on_table(cb)
    assert_on_table(ob)


def test_both_launched_balls_sink_and_are_both_lifted() -> None:
    """Two just-launched balls are both rewound below the table and both lifted in turn.

    Each lift pivots on the other ball's current position and preserves the separation,
    so after both lifts the balls rest at z == R at exactly the target separation, and
    each ball's net displacement lies in the vertical plane of its own velocity.
    """
    ob = make_ball((0.0, 0.0, R + 1e-7), vel=(-0.4, 0.5, 0.7), s=airborne)
    cb = ball_offset_from(
        ob, (-0.9, 0.44, 0.0), penetrance=1e-7, vel=(0.9, 0.3, 1.2), s=airborne
    )
    cb_before, ob_before = cb.copy(), ob.copy()

    MODEL.make_kiss(cb, ob)

    assert_kissing(cb, ob)
    assert_on_table(cb)
    assert_on_table(ob)
    assert_displaced_within_velocity_plane(cb_before, cb)
    assert_displaced_within_velocity_plane(ob_before, ob)


def test_ball_directly_above_resting_ball() -> None:
    """A vertical line of centers has no horizontal direction to preserve.

    The descending ball is far enough away that the velocity correction shifts the
    midpoint by more than 5x the spacer, so the fallback pushes the resting ball
    straight down. Lifting it back pivots on a point directly above it, where the
    plane of the centers is undefined; an arbitrary horizontal direction must be chosen
    rather than producing a non-finite position.
    """
    ob = resting_ball()
    cb = make_ball((0.0, 0.0, R + 2 * R + 2e-5), vel=(0.0, 0.0, -1.0), s=airborne)

    MODEL.make_kiss(cb, ob)

    assert np.all(np.isfinite(cb.state.rvw[0]))
    assert np.all(np.isfinite(ob.state.rvw[0]))
    assert_kissing(cb, ob)
    assert_on_table(ob)
    assert cb.state.rvw[0, 2] >= R


def test_on_table_stress() -> None:
    """Random on-table pairs end at the target separation with both balls on the table."""
    rng = np.random.default_rng(42)
    states = (sliding, rolling, stationary)

    for _ in range(100):
        penetrance = float(rng.uniform(-0.01, 0.005))
        angle = float(rng.uniform(0, 2 * np.pi))
        direction = (float(np.cos(angle)), float(np.sin(angle)), 0.0)
        s1, s2 = states[int(rng.integers(0, 3))], states[int(rng.integers(0, 3))]
        v1 = rng.standard_normal(2) * (s1 != stationary)
        v2 = rng.standard_normal(2) * (s2 != stationary)

        ob = make_ball((0.0, 0.0, R), (float(v2[0]), float(v2[1]), 0.0), s2)
        cb = ball_offset_from(
            ob, direction, penetrance, (float(v1[0]), float(v1[1]), 0.0), s1
        )

        MODEL.make_kiss(cb, ob)

        assert_kissing(cb, ob)
        assert_on_table(cb)
        assert_on_table(ob)


def test_airborne_stress() -> None:
    """Random airborne balls meeting resting or airborne balls satisfy both constraints."""
    rng = np.random.default_rng(42)

    for _ in range(100):
        penetrance = float(rng.uniform(-0.01, 0.005))
        other_airborne = bool(rng.integers(0, 2))
        z2 = R + float(rng.uniform(0.0, 0.5 * R)) if other_airborne else R
        v2 = rng.standard_normal(3) if other_airborne else np.zeros(3)
        ob = make_ball(
            (0.0, 0.0, z2),
            (float(v2[0]), float(v2[1]), float(v2[2])),
            airborne if other_airborne else stationary,
        )

        elevation = float(rng.uniform(-np.pi / 6, np.pi / 3))
        azimuth = float(rng.uniform(0, 2 * np.pi))
        direction = (
            float(np.cos(elevation) * np.cos(azimuth)),
            float(np.cos(elevation) * np.sin(azimuth)),
            float(np.sin(elevation)),
        )
        v1 = rng.standard_normal(3) * float(rng.uniform(0.1, 2.0))
        cb = ball_offset_from(
            ob,
            direction,
            penetrance,
            (float(v1[0]), float(v1[1]), float(v1[2])),
            airborne,
        )
        if cb.state.rvw[0, 2] < R:
            continue

        MODEL.make_kiss(cb, ob)

        assert_kissing(cb, ob)
        assert cb.state.rvw[0, 2] >= R - 1e-12
        if other_airborne:
            assert ob.state.rvw[0, 2] >= R - 1e-12
        else:
            assert_on_table(ob)


def test_thin_cut_rejects_velocity_plane_and_uses_plane_of_centers() -> None:
    """When the velocity-plane circle cannot reach the table, the plane of centers is used.

    Both balls are rewound below the table, with the cue ball deeper. Its horizontal
    velocity is exactly perpendicular to the horizontal line of centers, so the vertical
    plane of its velocity is tangent-like to the sphere and cuts a circle whose radius
    equals the balls' height difference. That circle is centered at the object ball's
    sunk height and cannot reach z == R, so the cue ball must slide along the great
    circle in the plane of the centers instead. That plane holds y == 0, whereas a lift
    in the velocity plane would have moved the cue ball in y.

    The scene is built backward from the post-rewind configuration so the sunk depths
    are known exactly.
    """
    penetrance = 1e-7
    rewind_time = 1e-6
    depth_ob, depth_cb = 6e-7, 7e-7

    ob_sunk = np.array([0.0, 0.0, R - depth_ob])
    dz = -(depth_cb - depth_ob)
    cb_sunk = ob_sunk + np.array([-np.sqrt(TARGET**2 - dz**2), 0.0, dz])

    v_cb = np.array([0.0, 1.0, 1.0])
    relative_direction = ptmath.unit_vector(cb_sunk - ob_sunk)
    closing_speed = (penetrance + MIN_DIST) / rewind_time
    v_ob = v_cb + closing_speed * relative_direction

    cb_start = cb_sunk + rewind_time * v_cb
    ob_start = ob_sunk + rewind_time * v_ob
    assert cb_start[2] > R and ob_start[2] > R
    assert np.linalg.norm(cb_start - ob_start) == pytest.approx(2 * R - penetrance)

    cb = make_ball(tuple(cb_start), tuple(v_cb), airborne)
    ob = make_ball(tuple(ob_start), tuple(v_ob), airborne)

    MODEL.make_kiss(cb, ob)

    assert_kissing(cb, ob)
    assert_on_table(cb)
    assert_on_table(ob)
    assert cb.state.rvw[0, 1] == pytest.approx(0.0, abs=1e-12)


def test_separated_on_table_ball_is_advanced_forward() -> None:
    """Balls separated by more than the target are advanced along the velocity, not rewound.

    The gap exceeds the spacer, so the smallest-magnitude root is positive and the
    moving ball travels forward along its velocity to reach the target separation.
    """
    ob = resting_ball()
    cb = ball_offset_from(
        ob, (-1, 0, 0), penetrance=-(MIN_DIST + 3e-7), vel=(1.0, 0.0, 0.0)
    )
    cb_before, ob_before = cb.copy(), ob.copy()

    MODEL.make_kiss(cb, ob)

    displacement = cb.state.rvw[0] - cb_before.state.rvw[0]
    assert np.dot(displacement, cb_before.state.rvw[1]) > 0
    assert_kissing(cb, ob)
    assert_on_table(cb)
    assert np.array_equal(ob.state.rvw[0], ob_before.state.rvw[0])
    assert_displaced_along_velocity(cb_before, cb)


def test_separated_landing_ball_advanced_below_table_is_lifted() -> None:
    """A descending ball advanced forward can pass through the table and must be lifted.

    The mirror image of the just-launched case: the ball is barely above resting
    height with a downward velocity and separated from the resting ball by more than
    the target, so the positive time offset carries it below z == R. It is lifted within
    the vertical plane of its velocity.
    """
    ob = resting_ball()
    cb = ball_offset_from(
        ob, (-1, 0, 0), penetrance=-(MIN_DIST + 3e-7), vel=(1.0, 0.4, -0.8), s=airborne
    )
    cb.state.rvw[0, 2] = R + 5e-8
    cb_before, ob_before = cb.copy(), ob.copy()

    MODEL.make_kiss(cb, ob)

    displacement = cb.state.rvw[0] - cb_before.state.rvw[0]
    assert np.dot(displacement, cb_before.state.rvw[1]) > 0
    assert_kissing(cb, ob)
    assert_on_table(cb)
    assert np.array_equal(ob.state.rvw[0], ob_before.state.rvw[0])
    assert_displaced_within_velocity_plane(cb_before, cb)
