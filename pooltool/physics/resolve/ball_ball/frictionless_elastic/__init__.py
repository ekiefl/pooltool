from typing import Tuple

import attrs
import numpy as np

import pooltool.constants as c
import pooltool.math as math
from pooltool.objects.ball.datatypes import Ball, BallState


def _resolve_ball_ball(rvw1, rvw2, R, spacer: bool = True):
    """Frictionless, instantaneous, elastic, equal mass collision

    Args:
        spacer:
            A correction is made such that if the balls are not 2*R apart, they are
            moved equally along their line of centers such that they are, at least to
            within float precision error. That's where this paramter comes in. If spacer
            is True, a small epsilon of additional distance (constants.EPS_SPACE) is put
            between them, ensuring the balls are non-intersecting.
    """

    r1, r2 = rvw1[0], rvw2[0]
    v1, v2 = rvw1[1], rvw2[1]

    n = math.unit_vector(r2 - r1)
    t = math.coordinate_rotation(n, np.pi / 2)

    correction = 2 * R - math.norm3d(r2 - r1) + (c.EPS_SPACE if spacer else 0.0)
    rvw2[0] += correction / 2 * n
    rvw1[0] -= correction / 2 * n

    v_rel = v1 - v2
    v_mag = math.norm3d(v_rel)

    beta = math.angle(v_rel, n)

    rvw1[1] = t * v_mag * np.sin(beta) + v2
    rvw2[1] = n * v_mag * np.cos(beta) + v2

    return rvw1, rvw2


def resolve_ball_ball(
    ball1: Ball, ball2: Ball, inplace: bool = False
) -> Tuple[Ball, Ball]:
    if not inplace:
        ball1 = ball1.copy()
        ball2 = ball2.copy()

    rvw1, rvw2 = _resolve_ball_ball(
        ball1.state.rvw.copy(),
        ball2.state.rvw.copy(),
        ball1.params.R,
    )

    ball1.state = BallState(rvw1, c.sliding)
    ball2.state = BallState(rvw2, c.sliding)

    return ball1, ball2


class FrictionlessElastic:
    def resolve(
        self, ball1: Ball, ball2: Ball, inplace: bool = False
    ) -> Tuple[Ball, Ball]:
        return resolve_ball_ball(ball1, ball2, inplace=inplace)
