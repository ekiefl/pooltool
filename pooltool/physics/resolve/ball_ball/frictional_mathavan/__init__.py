from typing import Tuple

import numpy as np
from numpy import sqrt, dot
import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball, BallState
from pooltool.physics.resolve.ball_ball.core import CoreBallBallCollision
from pooltool.physics.resolve.ball_ball.frictional_mathavan.collisions import collide_balls, collide_balls_f90

def _resolve_ball_ball(rvw1, rvw2, R, m):
    r_i, v_i, omega_i = rvw1.copy()
    r_j, v_j, omega_j = rvw2.copy()

    r_i[2], r_i[1] = r_i[1], r_i[2]
    v_i[2], v_i[1] = v_i[1], 0
    omega_i[2], omega_i[1] = omega_i[1], omega_i[2]

    r_j[2], r_j[1] = r_j[1], r_j[2]
    v_j[2], v_j[1] = v_j[1], 0
    omega_j[2], omega_j[1] = omega_j[1], omega_j[2]

    # print(v_i)
    r_ij = r_j - r_i
    y_loc = r_ij / sqrt(dot(r_ij, r_ij))
    v_ij = v_j - v_i
    v_ij_y0 = dot(v_ij, y_loc)

    v_i1, omega_i1, v_j1, omega_j1 = collide_balls_f90(
        r_i, v_i, omega_i, r_j, v_j, omega_j,
        m*abs(v_ij_y0)/6400
    )

    # v_i1, omega_i1, v_j1, omega_j1 = collide_balls(r_i, v_i, omega_i, r_j, v_j, omega_j)
    omega_i1[1], omega_i1[2] = omega_i1[2], omega_i1[1]
    omega_j1[1], omega_j1[2] = omega_j1[2], omega_j1[1]

    rvw1[1,:2] = v_i1[::2]
    rvw1[2] = omega_i1
    rvw2[1,:2] = v_j1[::2]
    rvw2[2] = omega_j1
    return rvw1, rvw2

    # r1, r2 = rvw1[0], rvw2[0]
    # v1, v2 = rvw1[1], rvw2[1]

    # n = ptmath.unit_vector(r2 - r1)
    # t = ptmath.coordinate_rotation(n, np.pi / 2)

    # v_rel = v1 - v2
    # v_mag = ptmath.norm3d(v_rel)

    # beta = ptmath.angle(v_rel, n)

    # rvw1[1] = t * v_mag * np.sin(beta) + v2
    # rvw2[1] = n * v_mag * np.cos(beta) + v2




class FrictionalMathavan(CoreBallBallCollision):
    def solve(self, ball1: Ball, ball2: Ball) -> Tuple[Ball, Ball]:
        rvw1, rvw2 = _resolve_ball_ball(
            ball1.state.rvw.copy(),
            ball2.state.rvw.copy(),
            ball1.params.R,
            ball1.params.m
        )

        ball1.state = BallState(rvw1, const.sliding)
        ball2.state = BallState(rvw2, const.sliding)

        return ball1, ball2
