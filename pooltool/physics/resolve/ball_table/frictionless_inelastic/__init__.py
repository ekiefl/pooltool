from typing import Tuple

import pooltool.constants as const
from pooltool.objects.ball.datatypes import Ball, BallState
from pooltool.objects.table.datatypes import Table
from pooltool.physics.resolve.ball_table.core import CoreBallTableCollision


def _resolve_ball_table(vz0: float, e_t: float) -> float:
    if vz0 >= 0:
        raise ValueError(
            "Ball with positive z-velocity can't collide with table surface."
        )

    return -vz0 * e_t


def _bounce_height(vz: float, g: float) -> float:
    """Return how high a ball with outgoing positive z-velocity will bounce.

    Measured as distance from table to bottom of ball.
    """
    return 0.5 * vz**2 / g


class FrictionlessInelastic(CoreBallTableCollision):
    """A frictionless, inelastic collision.

    In this model the ball bounces on the table with a coefficient of restitution. There
    is no influence of friction and so only the z-component of the velocity is
    affected.

    To avoid infinite bouncing (aka the dichotomy paradox), the projected bounce height
    is calculated and if that is less than the min_bounce_height, the z-component of the
    velocity is zeroed and the outgoing ball state is set to sliding.
    """

    def __init__(self, min_bounce_height: float = 0.005):
        self.min_bounce_height = min_bounce_height

    def solve(self, ball: Ball, table: Table) -> Tuple[Ball, Table]:
        """Resolves the collision."""
        vz = _resolve_ball_table(ball.state.rvw[1, 2], ball.params.e_t)

        if _bounce_height(vz, ball.params.g) < self.min_bounce_height:
            vz = 0.0
            state = const.sliding
        else:
            state = const.airborne

        ball.state.rvw[1, 2] = vz
        ball.state = BallState(ball.state.rvw, state)

        return ball, table
