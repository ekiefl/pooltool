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


def head_on() -> Tuple[Ball, Ball]:
    cb = Ball.create("cue", xy=(0, 0))

    # Cue ball makes head-on collision with object ball at 1 m/s in +x direction
    cb.state.rvw[1] = np.array([1, 0, 0])

    ob = Ball.create("cue", xy=(2 * cb.params.R, 0))
    assert cb.params.m == ob.params.m, "Balls expected to be equal mass"
    return cb, ob


def translating_head_on() -> Tuple[Ball, Ball]:
    cb = Ball.create("cue", xy=(0, 0))
    ob = Ball.create("cue", xy=(2 * cb.params.R, 0))

    # Cue ball makes head-on collision with object ball at 1 m/s in +x direction
    # while both balls move together at 1 m/s in +y direction
    cb.state.rvw[1] = np.array([1, 1, 0])
    ob.state.rvw[1] = np.array([0, 1, 0])

    assert cb.params.m == ob.params.m, "Balls expected to be equal mass"
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
    assert np.isclose(cb_f.vel[1], ob_f.vel[1], atol=1e-10)


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
    assert cb_wz_f < cb_wz_i, "Spin should be decay"
