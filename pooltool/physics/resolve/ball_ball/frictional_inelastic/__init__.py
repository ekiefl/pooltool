from typing import Tuple

import numpy as np
from numba import jit

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball, BallState
from pooltool.physics.resolve.ball_ball.core import CoreBallBallCollision


@jit(nopython=True, cache=const.use_numba_cache)
def _resolve_ball_ball(rvw1, rvw2, R, u_b, e_b):
    unit_x = np.array([1.0, 0.0, 0.0])

    # rotate the x-axis to be in line with the line of centers
    delta_centers = rvw2[0] - rvw1[0]
    # FIXME3D: this should use quaternion rotation in 3D
    theta = ptmath.angle(delta_centers, unit_x)
    rvw1[1] = ptmath.coordinate_rotation(rvw1[1], -theta)
    rvw1[2] = ptmath.coordinate_rotation(rvw1[2], -theta)
    rvw2[1] = ptmath.coordinate_rotation(rvw2[1], -theta)
    rvw2[2] = ptmath.coordinate_rotation(rvw2[2], -theta)

    rvw1_f = rvw1.copy()
    rvw2_f = rvw2.copy()

    # velocity normal component, same for both slip and no-slip after collison cases
    v1_n_f = 0.5 * ((1.0 - e_b) * rvw1[1][0] + (1.0 + e_b) * rvw2[1][0])
    v2_n_f = 0.5 * ((1.0 + e_b) * rvw1[1][0] + (1.0 - e_b) * rvw2[1][0])
    D_v_n_magnitude = abs(v2_n_f - v1_n_f)

    # angular velocity normal component, unchanged
    w1_n_f = rvw1[2][0]
    w2_n_f = rvw2[2][0]

    # discard normal components for now
    # so that surface velocities are tangent
    rvw1[1][0] = 0.0
    rvw1[2][0] = 0.0
    rvw2[1][0] = 0.0
    rvw2[2][0] = 0.0
    rvw1_f[1][0] = 0.0
    rvw1_f[2][0] = 0.0
    rvw2_f[1][0] = 0.0
    rvw2_f[2][0] = 0.0

    v1_c = ptmath.surface_velocity(rvw1, unit_x, R)
    v2_c = ptmath.surface_velocity(rvw2, -unit_x, R)
    v12_c = v1_c - v2_c
    has_relative_velocity = ptmath.norm3d(v12_c) > const.EPS

    # if there is no relative surface velocity to begin with,
    # don't bother calculating slip condition
    if has_relative_velocity:
        # tangent components for slip condition
        v12_c_hat = ptmath.unit_vector(v12_c)
        D_v1_t = u_b * D_v_n_magnitude * -v12_c_hat
        D_w1 = 2.5 / R * ptmath.cross(unit_x, D_v1_t)
        rvw1_f[1] = rvw1[1] + D_v1_t
        rvw1_f[2] = rvw1[2] + D_w1
        rvw2_f[1] = rvw2[1] - D_v1_t
        rvw2_f[2] = rvw2[2] + D_w1

        # calculate new relative contact velocity
        v1_c_slip = ptmath.surface_velocity(rvw1_f, unit_x, R)
        v2_c_slip = ptmath.surface_velocity(rvw2_f, -unit_x, R)
        v12_c_slip = v1_c_slip - v2_c_slip

    # if there was no relative velocity to begin with, or if slip changed directions,
    # then slip condition is invalid so we need to calculate no-slip condition
    if not has_relative_velocity or np.dot(v12_c, v12_c_slip) <= 0:  # type: ignore
        # velocity tangent component for no-slip condition
        D_v1_t = -(1.0 / 9.0) * (
            2.0 * (rvw1[1] - rvw2[1])
            + R * ptmath.cross(2.0 * rvw1[2] + 7.0 * rvw2[2], unit_x)
        )
        D_w1 = (5.0 / 9.0) * (
            rvw2[2] - rvw1[2] + ptmath.cross(unit_x, rvw2[1] - rvw1[1]) / R
        )
        rvw1_f[1] = rvw1[1] + D_v1_t
        rvw1_f[2] = rvw1[2] + D_w1
        rvw2_f[1] = rvw2[1] - D_v1_t
        rvw2_f[2] = rvw2[2] + D_w1

    # reintroduce the final normal components
    rvw1_f[1][0] = v1_n_f
    rvw2_f[1][0] = v2_n_f
    rvw1_f[2][0] = w1_n_f
    rvw2_f[2][0] = w2_n_f

    # rotate everything back to the original frame
    rvw1_f[1] = ptmath.coordinate_rotation(rvw1_f[1], theta)
    rvw1_f[2] = ptmath.coordinate_rotation(rvw1_f[2], theta)
    rvw2_f[1] = ptmath.coordinate_rotation(rvw2_f[1], theta)
    rvw2_f[2] = ptmath.coordinate_rotation(rvw2_f[2], theta)

    # FIXME3D: include z velocity components
    # remove any z velocity components from spin-induced throw
    rvw1_f[1][2] = 0.0
    rvw2_f[1][2] = 0.0

    return rvw1_f, rvw2_f


class FrictionalInelastic(CoreBallBallCollision):
    """A simple ball-ball collision model including ball-ball friction, and coefficient of restitution for equal-mass balls

    Largely inspired by Dr. David Alciatore's technical proofs (https://billiards.colostate.edu/technical_proofs),
    in particular, TP_A-5, TP_A-6, and TP_A-14. These ideas have been extended to include motion of both balls,
    and a more complete analysis of velocity and angular velocity in their vector forms.
    """

    def solve(self, ball1: Ball, ball2: Ball) -> Tuple[Ball, Ball]:
        """Resolves the collision."""
        rvw1, rvw2 = _resolve_ball_ball(
            ball1.state.rvw.copy(),
            ball2.state.rvw.copy(),
            ball1.params.R,
            # Assume the interaction coefficients are the average of the two balls
            u_b=(ball1.params.u_b + ball2.params.u_b) / 2,
            e_b=(ball1.params.e_b + ball2.params.e_b) / 2,
        )

        ball1.state = BallState(rvw1, const.sliding)
        ball2.state = BallState(rvw2, const.sliding)

        return ball1, ball2
