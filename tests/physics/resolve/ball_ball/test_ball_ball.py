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


@pytest.mark.parametrize("model", [FrictionlessElastic(), FrictionalMathavan()])
def test_head_on_zero_spin(model: BallBallCollisionStrategy):
    cb_i, ob_i = head_on()
    cb_f, ob_f = model.resolve(cb_i, ob_i, inplace=False)

    # Since balls are of equal mass, final cue ball +x speed should not be positive
    assert cb_f.state.rvw[1][0] <= 0


@pytest.mark.parametrize("model", [FrictionalMathavan()])
def test_head_on_z_spin(model: BallBallCollisionStrategy):
    cb_i, ob_i = head_on()

    # Apply +z spin (e.g. hitting right side of cue ball)
    wz_i = 0.1
    cb_i.state.rvw[2][2] = wz_i

    cb_f, ob_f = model.resolve(cb_i, ob_i, inplace=False)

    wz_f = cb_f.state.rvw[2][2]
    assert wz_f > 0, "Spin direction shouldn't reverse"
    assert wz_f < wz_i, "Spin should be decay"
