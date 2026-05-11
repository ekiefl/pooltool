import attrs
import numpy as np
import quaternion

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball, BallState
from pooltool.physics.resolve.ball_ball.core import CoreBallBallCollision
from pooltool.physics.resolve.models import BallBallModel


def _resolve_ball_ball(rvw1, m1, rvw2, m2):
    unit_x = np.array([1.0, 0.0, 0.0])
    delta_centers = rvw2[0] - rvw1[0]
    frame_rotation = ptmath.quaternion_from_vector_to_vector(delta_centers, unit_x)
    v1 = quaternion.rotate_vectors(frame_rotation, rvw1[1])
    v2 = quaternion.rotate_vectors(frame_rotation, rvw2[1])
    v1, v2 = _resolve_ball_ball_x_normal(v1, m1, v2, m2)
    v1 = quaternion.rotate_vectors(frame_rotation.conjugate(), v1)
    v2 = quaternion.rotate_vectors(frame_rotation.conjugate(), v2)
    rvw1[1] = v1
    rvw2[1] = v2
    return rvw1, rvw2


def _resolve_ball_ball_x_normal(v1, m1, v2, m2):
    v_12_n = v1[0] - v2[0]
    D_v1_n = -2.0 / (1 + m1 / m2) * v_12_n
    D_v2_n = -(m1 / m2) * D_v1_n
    v1[0] += D_v1_n
    v2[0] += D_v2_n
    return v1, v2


@attrs.define
class FrictionlessElastic(CoreBallBallCollision):
    """A frictionless, instantaneous, elastic collision resolver.

    This is as simple as it gets.

    See Also:
        - This physics of this model is blogged about at
          https://ekiefl.github.io/2020/04/24/pooltool-theory/#1-elastic-instantaneous-frictionless.
          It's since been modified to handle balls of unequal mass and size.
    """

    model: BallBallModel = attrs.field(
        default=BallBallModel.FRICTIONLESS_ELASTIC, init=False, repr=False
    )

    def solve(self, ball1: Ball, ball2: Ball) -> tuple[Ball, Ball]:
        """Resolves the collision."""
        rvw1, rvw2 = _resolve_ball_ball(
            ball1.state.rvw.copy(),
            ball1.params.m,
            ball2.state.rvw.copy(),
            ball2.params.m,
        )

        ball1.state = BallState(rvw1, const.sliding)
        ball2.state = BallState(rvw2, const.sliding)

        # FIXME3D: include z velocity components
        rvw1[1][2] = 0.0
        rvw2[1][2] = 0.0

        return ball1, ball2
