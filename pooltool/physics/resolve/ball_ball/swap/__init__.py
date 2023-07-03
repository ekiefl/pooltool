from typing import Tuple

from pooltool.objects.ball.datatypes import Ball
from pooltool.physics.resolve.ball_ball.frictionless_elastic import resolve_ball_ball


class FrictionlessElasticSwap:
    """Solves the collision and then unrealistically swaps the balls"""

    def resolve(
        self, ball1: Ball, ball2: Ball, inplace: bool = False
    ) -> Tuple[Ball, Ball]:
        ball1, ball2 = resolve_ball_ball(ball1, ball2, inplace=inplace)

        ball1_state = ball1.state.copy()
        ball2_state = ball2.state.copy()

        ball1.state = ball2_state
        ball2.state = ball1_state

        return ball1, ball2
