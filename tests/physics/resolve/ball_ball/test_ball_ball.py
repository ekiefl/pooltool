from typing import Tuple

import numpy as np
import pytest

from pooltool.objects.ball.datatypes import Ball
from pooltool.physics.resolve.ball_ball.core import BallBallCollisionStrategy
from pooltool.physics.resolve.ball_ball.frictional_mathavan import FrictionalMathavan
from pooltool.physics.resolve.ball_ball.frictionless_elastic import FrictionlessElastic


def head_on() -> Tuple[Ball, Ball]:
    cb = Ball.create("cue", xy=(0, 0))

    # Cue ball makes head-on collision with object ball at 1 m/s in +x direction
    cb.state.rvw[1] = np.array([1, 0, 0])

    ob = Ball.create("cue", xy=(2 * cb.params.R, 0))
    assert cb.params.m == ob.params.m, "Balls expected to be equal mass"
    return cb, ob


@pytest.mark.parametrize("model", [FrictionlessElastic()])
def test_head_on_zero_spin(model: BallBallCollisionStrategy):
    cb_i, ob_i = head_on()
    cb_f, ob_f = model.resolve(cb_i, ob_i, inplace=False)

    # Since balls are of equal mass, final cue ball +x speed should not be positive
    assert cb_f.state.rvw[1][0] <= 0


@pytest.mark.parametrize("model", [FrictionalMathavan()])
def test_head_on_z_spin(model: BallBallCollisionStrategy):
    """Cue ball has positive z-spin (e.g. hitting right-hand-side of cue ball)"""
    cb_i, ob_i = head_on()
    cb_i.state.rvw[2][2] = (cb_wz_i := 0.1)

    cb_f, ob_f = model.resolve(cb_i, ob_i, inplace=False)

    assert ob_f.state.rvw[1][1] > 0, "Object ball should be thrown left"

    ob_wz_f = ob_f.state.rvw[2][2]
    opposing_zspin = np.sign(ob_wz_f) == -np.sign(cb_wz_i)
    assert opposing_zspin, "Final OB z-spin should oppose initial CB z-spin"

    cb_wz_f = cb_f.state.rvw[2][2]
    assert cb_wz_f > 0, "Spin direction shouldn't reverse"
    assert cb_wz_f < cb_wz_i, "Spin should be decay"
