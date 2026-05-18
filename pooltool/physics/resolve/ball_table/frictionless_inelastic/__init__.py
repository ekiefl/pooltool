import attrs

from pooltool.objects.ball.datatypes import Ball, BallState
from pooltool.physics.dimensionality import Dim
from pooltool.physics.resolve.ball_table.core import (
    CoreBallTableCollision,
    bounce_height,
    final_ball_motion_state,
)
from pooltool.physics.resolve.models import BallTableModel


def _resolve_ball_table(vz0: float, e_t: float) -> float:
    if vz0 >= 0:
        raise ValueError(
            "Ball with non-negative z-velocity can't collide with table surface."
        )

    return -vz0 * e_t


@attrs.define
class FrictionlessInelasticTable(CoreBallTableCollision):
    """A frictionless, inelastic collision.

    The ball bounces on the table with a coefficient of restitution. There is no
    influence of friction, so only the z-component of the velocity is affected.

    To avoid infinite bouncing (the dichotomy paradox), the projected bounce height
    is calculated; if it is less than ``min_bounce_height``, the z-component of the
    velocity is zeroed and the outgoing ball state is set accordingly.
    """

    min_bounce_height: float = 0.005

    model: BallTableModel = attrs.field(
        default=BallTableModel.FRICTIONLESS_INELASTIC, init=False, repr=False
    )
    dim: Dim = attrs.field(default=Dim.THREE, init=False, repr=False)

    def solve(self, ball: Ball) -> Ball:
        """Resolves the collision."""
        vz = _resolve_ball_table(ball.state.rvw[1, 2], ball.params.e_t)

        if bounce_height(vz, ball.params.g) < self.min_bounce_height:
            vz = 0.0

        ball.state.rvw[1, 2] = vz

        state = final_ball_motion_state(ball.state.rvw, ball.params.R)

        ball.state = BallState(ball.state.rvw, state)

        return ball
