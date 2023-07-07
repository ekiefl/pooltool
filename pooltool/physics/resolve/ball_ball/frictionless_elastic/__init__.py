from typing import Tuple

import numpy as np

import pooltool.constants as const
import pooltool.math as math
from pooltool.objects.ball.datatypes import Ball, BallState


def _resolve_ball_ball(rvw1, rvw2, R):
    """Frictionless, instantaneous, elastic, equal mass collision"""

    r1, r2 = rvw1[0], rvw2[0]
    v1, v2 = rvw1[1], rvw2[1]

    n = math.unit_vector(r2 - r1)
    t = math.coordinate_rotation(n, np.pi / 2)

    v_rel = v1 - v2
    v_mag = math.norm3d(v_rel)

    beta = math.angle(v_rel, n)

    rvw1[1] = t * v_mag * np.sin(beta) + v2
    rvw2[1] = n * v_mag * np.cos(beta) + v2

    return rvw1, rvw2


class FrictionlessElastic:
    def resolve(
        self, ball1: Ball, ball2: Ball, inplace: bool = False
    ) -> Tuple[Ball, Ball]:
        if not inplace:
            ball1 = ball1.copy()
            ball2 = ball2.copy()

        ball1, ball2 = self.make_kiss(ball1, ball2)

        rvw1, rvw2 = _resolve_ball_ball(
            ball1.state.rvw.copy(),
            ball2.state.rvw.copy(),
            ball1.params.R,
        )

        ball1.state = BallState(rvw1, const.sliding)
        ball2.state = BallState(rvw2, const.sliding)

        return ball1, ball2

    def make_kiss(self, ball1: Ball, ball2: Ball) -> Tuple[Ball, Ball]:
        """Translate the balls so they are (almost) touching

        This makes a correction such that if the balls are not 2*R apart, they are moved
        equally along their line of centers such that they are. To avoid float precision
        round-off error, a small epsilon of additional distance (constants.EPS_SPACE) is
        put between them, ensuring the balls are non-intersecting.
        """
        r1, r2 = ball1.state.rvw[0], ball2.state.rvw[0]
        n = math.unit_vector(r2 - r1)

        correction = 2 * ball1.params.R - math.norm3d(r2 - r1) + const.EPS_SPACE
        ball2.state.rvw[0] += correction / 2 * n
        ball1.state.rvw[0] -= correction / 2 * n

        return ball1, ball2
