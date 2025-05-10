import math
from typing import Tuple

import attrs
import numpy as np
import pytest

from pooltool import ptmath
from pooltool.objects.ball.datatypes import Ball
from pooltool.physics.resolve.ball_ball.core import BallBallCollisionStrategy
from pooltool.physics.resolve.ball_ball.frictional_inelastic import FrictionalInelastic
from pooltool.physics.resolve.ball_ball.frictional_mathavan import FrictionalMathavan
from pooltool.physics.resolve.ball_ball.frictionless_elastic import FrictionlessElastic


def vector_from_magnitude_and_direction(magnitude: float, angle_radians: float):
    """Convert magnitude and angle to a vector

    Angle is defined CCW from the x-axis in the xy-plane
    """
    return magnitude * np.array([math.cos(angle_radians), math.sin(angle_radians), 0.0])


def velocity_from_speed_and_xy_direction(speed: float, angle_radians: float):
    """Convert speed and angle to a velocity vector

    Angle is defined CCW from the x-axis in the xy-plane
    """
    return vector_from_magnitude_and_direction(speed, angle_radians)


def gearing_z_spin_for_incoming_ball(
    incoming_ball, line_of_centers_angle_radians: float
):
    """Calculate the amount of sidespin (z-axis spin) required for gearing contact
    with no relative surface velocity.

    In order for gearing contact to occur, the sidespin must cancel out any
    velocity in the tangential direction.

    s_tangent + w_z * R = 0, and therefore w_z = -s_tangent / R,
    where s_tangent is tangent relative surface speed due to linear velocity
    """
    unit_direction = vector_from_magnitude_and_direction(
        1.0, line_of_centers_angle_radians
    )
    s_tangent = np.linalg.vector_norm(
        incoming_ball.vel
        - np.linalg.vecdot(incoming_ball.vel, unit_direction) * unit_direction
    )
    return -s_tangent / incoming_ball.params.R


def ball_collision(line_of_centers_angle_radians: float) -> Tuple[Ball, Ball]:
    cb = Ball.create("cue", xy=(0, 0))
    offset_direction = vector_from_magnitude_and_direction(
        2 * cb.params.R, line_of_centers_angle_radians
    )
    ob = Ball.create("cue", xy=(offset_direction[0], offset_direction[1]))
    assert cb.params.m == ob.params.m, "Balls expected to be equal mass"
    return cb, ob


def head_on() -> Tuple[Ball, Ball]:
    cb, ob = ball_collision(0.0)
    # Cue ball makes head-on collision with object ball at 1 m/s in +x direction
    cb.state.rvw[1] = np.array([1, 0, 0])
    return cb, ob


def translating_head_on() -> Tuple[Ball, Ball]:
    cb, ob = ball_collision(0.0)
    # Cue ball makes head-on collision with object ball at 1 m/s in +x direction
    # while both balls move together at 1 m/s in +y direction
    cb.state.rvw[1] = np.array([1, 1, 0])
    ob.state.rvw[1] = np.array([0, 1, 0])
    return cb, ob


@pytest.mark.parametrize("model", [FrictionlessElastic()])
def test_head_on_zero_spin(model: BallBallCollisionStrategy):
    cb_i, ob_i = head_on()
    cb_f, ob_f = model.resolve(cb_i, ob_i, inplace=False)

    # Since balls are of equal mass, final cue ball +x speed should not be positive
    assert cb_f.state.rvw[1][0] <= 0


@pytest.mark.parametrize(
    "model", [FrictionalInelastic(), FrictionalMathavan(num_iterations=int(1e6))]
)
@pytest.mark.parametrize("e_b", [0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
def test_head_on_zero_spin_inelastic(model: BallBallCollisionStrategy, e_b: float):
    cb_i, ob_i = head_on()

    # Update coefficient of restitutions
    cb_i.params = attrs.evolve(cb_i.params, e_b=e_b)
    ob_i.params = attrs.evolve(ob_i.params, e_b=e_b)

    cb_f, ob_f = model.resolve(cb_i, ob_i, inplace=False)

    v_approach = ptmath.norm3d(cb_i.vel - ob_i.vel)
    v_separation = ptmath.norm3d(cb_f.vel - ob_f.vel)

    # coefficient of restitution definition
    expected_v_separation = v_approach * e_b

    assert np.isclose(expected_v_separation, v_separation, atol=1e-10)

    # Object ball should have +x velocity
    assert ob_f.state.rvw[1][0] > 0

    if e_b == 1.0:
        assert np.isclose(cb_f.state.rvw[1][0], 0, atol=1e-10)
    else:
        # Cue ball should have +x velocity, too (because of inelasticity)
        assert cb_f.state.rvw[1][0] > 0


@pytest.mark.parametrize("model", [FrictionalInelastic(), FrictionalMathavan()])
@pytest.mark.parametrize("e_b", [0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
def test_translating_head_on_zero_spin_inelastic(
    model: BallBallCollisionStrategy, e_b: float
):
    cb_i, ob_i = translating_head_on()

    # Update coefficient of restitutions
    cb_i.params = attrs.evolve(cb_i.params, e_b=e_b)
    ob_i.params = attrs.evolve(ob_i.params, e_b=e_b)

    cb_f, ob_f = model.resolve(cb_i, ob_i, inplace=False)

    # Balls should still be moving together in +y direction
    assert abs(cb_f.vel[1] - ob_f.vel[1]) < 1e-10


@pytest.mark.parametrize("model", [FrictionalInelastic(), FrictionalMathavan()])
@pytest.mark.parametrize("cb_wz_i", [0.1, 1, 10, 100])
def test_head_on_z_spin(model: BallBallCollisionStrategy, cb_wz_i: float):
    """Cue ball has positive z-spin (e.g. hitting right-hand-side of cue ball)"""
    cb_i, ob_i = head_on()
    cb_i.state.rvw[2][2] = cb_wz_i

    cb_f, ob_f = model.resolve(cb_i, ob_i, inplace=False)

    assert ob_f.state.rvw[1][1] > 0, "Object ball should be thrown left"

    ob_wz_f = ob_f.state.rvw[2][2]
    opposing_zspin = np.sign(ob_wz_f) == -np.sign(cb_wz_i)
    assert opposing_zspin, "Final OB z-spin should oppose initial CB z-spin"

    cb_wz_f = cb_f.state.rvw[2][2]
    assert cb_wz_f > 0, "Spin direction shouldn't reverse"
    assert cb_wz_f < cb_wz_i, "Spin should decay"


@pytest.mark.parametrize(
    "model", [FrictionalInelastic(), FrictionalMathavan(num_iterations=int(1e5))]
)
@pytest.mark.parametrize("speed", np.logspace(-1, 1, 5))
@pytest.mark.parametrize(
    "line_of_centers_angle_radians", np.linspace(0, 2.0 * math.pi, 8, endpoint=False)
)
@pytest.mark.parametrize(
    "cut_angle_radians", np.linspace(0, math.pi / 2.0, 8, endpoint=False)
)
def test_gearing_z_spin(
    model: BallBallCollisionStrategy,
    speed: float,
    line_of_centers_angle_radians: float,
    cut_angle_radians: float,
):
    """Ensure that a gearing collision causes no throw or induced spin.

    A gearing collision is one where the relative surface speed between the balls is 0.
    In other words, the velocity of each ball at the contact point is identical, and there is no
    slip at the contact point.
    """

    unit_normal = vector_from_magnitude_and_direction(
        1.0, line_of_centers_angle_radians
    )
    cb_i, ob_i = ball_collision(line_of_centers_angle_radians)

    cb_i.state.rvw[1] = velocity_from_speed_and_xy_direction(
        speed, line_of_centers_angle_radians + cut_angle_radians
    )
    cb_i.state.rvw[2][2] = gearing_z_spin_for_incoming_ball(
        cb_i, line_of_centers_angle_radians
    )

    # sanity check the initial conditions
    v_c = ptmath.tangent_surface_velocity(cb_i.state.rvw, unit_normal, cb_i.params.R)
    assert ptmath.norm3d(v_c) < 1e-10, "Relative surface contact speed should be zero"

    cb_f, ob_f = model.resolve(cb_i, ob_i, inplace=False)

    assert np.allclose(
        np.cross(ob_f.vel, unit_normal), np.zeros_like(unit_normal), atol=1e-3
    ), "Gearing english shouldn't cause throw"
    assert abs(ob_f.avel[2]) < 5e-3, "Gearing english shouldn't cause induced side-spin"


@pytest.mark.parametrize("model", [FrictionalInelastic()])
@pytest.mark.parametrize("speed", np.logspace(0, 1, 5))
@pytest.mark.parametrize(
    "line_of_centers_angle_radians", np.linspace(0, 2.0 * math.pi, 8, endpoint=False)
)
@pytest.mark.parametrize(
    "cut_angle_radians", np.linspace(0, math.pi / 2.0, 8, endpoint=False)
)
@pytest.mark.parametrize("relative_surface_speed", np.linspace(0, 0.05, 5))
def test_low_relative_surface_velocity(
    model: BallBallCollisionStrategy,
    speed: float,
    line_of_centers_angle_radians: float,
    cut_angle_radians: float,
    relative_surface_speed: float,
):
    """Ensure that collisions with a "small" relative surface velocity end with 0 relative surface velocity.
    In other words, that the balls are gearing after the collision.

    Note that how small the initial relative surface velocity needs to be for this condition to be met is dependent
    on model parameters and initial conditions such as ball-ball friction and the collision speed along the line of centers.
    """

    unit_normal = vector_from_magnitude_and_direction(
        1.0, line_of_centers_angle_radians
    )
    cb_i, ob_i = ball_collision(line_of_centers_angle_radians)

    cb_i.state.rvw[1] = velocity_from_speed_and_xy_direction(
        speed, line_of_centers_angle_radians + cut_angle_radians
    )
    cb_i.state.rvw[2][2] = gearing_z_spin_for_incoming_ball(
        cb_i, line_of_centers_angle_radians
    )
    cb_i.state.rvw[2][2] += (
        relative_surface_speed / cb_i.params.R
    )  # from v = w * R -> w = v / R

    # sanity check the initial conditions
    v_c = ptmath.tangent_surface_velocity(cb_i.state.rvw, unit_normal, cb_i.params.R)
    assert (
        abs(relative_surface_speed - ptmath.norm3d(v_c)) < 1e-10
    ), f"Relative surface contact speed should be {relative_surface_speed}"

    cb_f, ob_f = model.resolve(cb_i, ob_i, inplace=False)

    cb_v_c_f = ptmath.tangent_surface_velocity(
        cb_f.state.rvw, unit_normal, cb_f.params.R
    )
    ob_v_c_f = ptmath.tangent_surface_velocity(
        ob_f.state.rvw, -unit_normal, ob_f.params.R
    )
    assert (
        ptmath.norm3d(cb_v_c_f - ob_v_c_f) < 1e-3
    ), "Final relative contact velocity should be zero"
