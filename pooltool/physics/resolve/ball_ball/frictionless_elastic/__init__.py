import attrs
import numpy as np

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball, BallState
from pooltool.physics.resolve.ball_ball.core import CoreBallBallCollision
from pooltool.physics.resolve.models import BallBallModel


def _resolve_ball_ball(rvw1, rvw2, R):
    r1, r2 = rvw1[0], rvw2[0]
    v1, v2 = rvw1[1], rvw2[1]

    n = ptmath.unit_vector(r2 - r1)
    t = ptmath.coordinate_rotation(n, np.pi / 2)

    v_rel = v1 - v2
    v_mag = ptmath.norm3d(v_rel)

    beta = ptmath.angle(v_rel, n)

    rvw1[1] = t * v_mag * np.sin(beta) + v2
    rvw2[1] = n * v_mag * np.cos(beta) + v2

    return rvw1, rvw2


@attrs.define
class FrictionlessElastic(CoreBallBallCollision):
    """A frictionless, instantaneous, elastic, equal mass collision resolver.

    This is as simple as it gets.

    See Also:
        - This physics of this model is blogged about at
          https://ekiefl.github.io/2020/04/24/pooltool-theory/#1-elastic-instantaneous-frictionless
    """

    model: BallBallModel = attrs.field(
        default=BallBallModel.FRICTIONLESS_ELASTIC, init=False, repr=False
    )

    def solve(self, ball1: Ball, ball2: Ball) -> tuple[Ball, Ball]:
        """Resolves the collision."""
        rvw1, rvw2 = _resolve_ball_ball(
            ball1.state.rvw.copy(),
            ball2.state.rvw.copy(),
            ball1.params.R,
        )

        ball1.state = BallState(rvw1, const.sliding)
        ball2.state = BallState(rvw2, const.sliding)

        return ball1, ball2
