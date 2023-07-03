from typing import Tuple

import numpy as np

import pooltool.constants as const
from pooltool.objects.ball.datatypes import Ball, BallState
from pooltool.objects.table.components import Pocket


def resolve_ball_pocket(
    ball: Ball, pocket: Pocket, inplace: bool = False
) -> Tuple[Ball, Pocket]:
    if not inplace:
        ball = ball.copy()
        pocket = pocket.copy()

    # Ball is placed at the pocket center
    rvw = np.array(
        [
            [pocket.a, pocket.b, -pocket.depth],
            [0, 0, 0],
            [0, 0, 0],
        ]
    )

    ball.state = BallState(rvw, const.pocketed)
    pocket.add(ball.id)

    return ball, pocket
