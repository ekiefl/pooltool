import attrs
import numpy as np
import quaternion
from numba import jit

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball
from pooltool.physics.dimensionality import Dim
from pooltool.physics.resolve.ball_ball.core import (
    CoreBallBallCollision,
    final_ball_motion_state,
)
from pooltool.physics.resolve.ball_ball.friction import (
    AlciatoreBallBallFriction,
    BallBallFrictionStrategy,
)
from pooltool.physics.resolve.models import BallBallModel
from pooltool.physics.utils import surface_velocity


def _resolve_ball_ball(rvw1, rvw2, R, u_b, e_b):
    unit_x = np.array([1.0, 0.0, 0.0])
    delta_centers = rvw2[0] - rvw1[0]
    frame_rotation = ptmath.quaternion_from_vector_to_vector(delta_centers, unit_x)
    rvw1 = quaternion.rotate_vectors(frame_rotation, rvw1)
    rvw2 = quaternion.rotate_vectors(frame_rotation, rvw2)
    rvw1, rvw2 = _resolve_ball_ball_x_normal(rvw1, rvw2, R, u_b, e_b)
    rvw1 = quaternion.rotate_vectors(frame_rotation.conjugate(), rvw1)
    rvw2 = quaternion.rotate_vectors(frame_rotation.conjugate(), rvw2)
    return rvw1, rvw2


@jit(nopython=True, cache=const.use_numba_cache)
def _resolve_ball_ball_x_normal(rvw1, rvw2, R, u_b, e_b):
    unit_x = np.array([1.0, 0.0, 0.0])

    # velocity normal component, same for both slip and no-slip after collison cases
    v1_n_f = 0.5 * ((1.0 - e_b) * rvw1[1][0] + (1.0 + e_b) * rvw2[1][0])
    v2_n_f = 0.5 * ((1.0 + e_b) * rvw1[1][0] + (1.0 - e_b) * rvw2[1][0])
    D_v_n_magnitude = abs(v2_n_f - v1_n_f)

    # angular velocity normal component, unchanged
    w1_n_f = rvw1[2][0]
    w2_n_f = rvw2[2][0]

    # discard velocity normal components for now
    rvw1[1][0] = 0.0
    rvw2[1][0] = 0.0
    rvw1[2][0] = 0.0
    rvw2[2][0] = 0.0
    rvw1_f = rvw1.copy()
    rvw2_f = rvw2.copy()

    v1_c = surface_velocity(rvw1, unit_x, R)
    v2_c = surface_velocity(rvw2, -unit_x, R)
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
        v1_c_slip = surface_velocity(rvw1_f, unit_x, R)
        v2_c_slip = surface_velocity(rvw2_f, -unit_x, R)
        v12_c_slip = v1_c_slip - v2_c_slip

    # if there was no relative velocity to begin with, or if slip changed directions,
    # then slip condition is invalid so we need to calculate no-slip condition
    if not has_relative_velocity or np.dot(v12_c, v12_c_slip) <= 0:  # type: ignore
        # velocity tangent component for no-slip condition
        D_v1_t = -(1.0 / 7.0) * (
            rvw1[1] - rvw2[1] + R * ptmath.cross(rvw1[2] + rvw2[2], unit_x)
        )
        D_w1 = -(5.0 / 14.0) * (
            ptmath.cross(unit_x, rvw1[1] - rvw2[1]) / R + rvw1[2] + rvw2[2]
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

    return rvw1_f, rvw2_f


@attrs.define
class FrictionalInelastic3D(CoreBallBallCollision):
    """A simple ball-ball collision model including ball-ball friction, and coefficient of restitution for equal-mass balls

    Largely inspired by Dr. David Alciatore's technical proofs
    (https://billiards.colostate.edu/technical_proofs), in particular, TP_A-5, TP_A-6,
    and TP_A-14. These ideas have been extended to include motion of both balls, and a
    more complete analysis of velocity and angular velocity in their vector forms.
    """

    friction: BallBallFrictionStrategy = AlciatoreBallBallFriction()

    model: BallBallModel = attrs.field(
        default=BallBallModel.FRICTIONAL_INELASTIC_3D, init=False, repr=False
    )
    dim: Dim = attrs.field(default=Dim.THREE, init=False, repr=False)

    def solve(self, ball1: Ball, ball2: Ball) -> tuple[Ball, Ball]:
        """Resolves the collision."""
        rvw1, rvw2 = _resolve_ball_ball(
            ball1.state.rvw.copy(),
            ball2.state.rvw.copy(),
            ball1.params.R,
            u_b=self.friction.calculate_friction(ball1, ball2),
            # Average the coefficient of restitution parameters for the two balls
            e_b=(ball1.params.e_b + ball2.params.e_b) / 2,
        )

        ball1.state.rvw = rvw1
        ball2.state.rvw = rvw2

        ball1.state.s = final_ball_motion_state(rvw1, ball1.params.R)
        ball2.state.s = final_ball_motion_state(rvw2, ball2.params.R)

        return ball1, ball2


@attrs.define
class FrictionalInelastic2D(FrictionalInelastic3D):
    """A simple ball-ball collision model including ball-ball friction, and coefficient of restitution for equal-mass balls

    For details see :class:`FrictionalInelastic3D`.
    """

    model: BallBallModel = attrs.field(
        default=BallBallModel.FRICTIONAL_INELASTIC_2D, init=False, repr=False
    )
    dim: Dim = attrs.field(default=Dim.TWO, init=False, repr=False)

    def solve(self, ball1: Ball, ball2: Ball) -> tuple[Ball, Ball]:
        """Resolves the collision."""
        ball1, ball2 = super().solve(ball1, ball2)

        # remove any z velocity components for 2D
        ball1.state.rvw[1, 2] = 0.0
        ball1.state.rvw[1, 2] = 0.0
        ball1.state.s = const.sliding
        ball2.state.s = const.sliding

        return ball1, ball2
