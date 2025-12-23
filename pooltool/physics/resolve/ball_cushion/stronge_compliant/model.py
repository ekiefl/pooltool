import logging

import attrs
import numpy as np

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball, BallState
from pooltool.objects.table.components import (
    CircularCushionSegment,
    Cushion,
    LinearCushionSegment,
)
from pooltool.physics.resolve.ball_cushion.core import (
    CoreBallCCushionCollision,
    CoreBallLCushionCollision,
)
from pooltool.physics.resolve.models import BallCCushionModel, BallLCushionModel
from pooltool.physics.resolve.stronge_compliant import (
    resolve_collinear_compliant_frictional_inelastic_collision,
)

logger = logging.getLogger(__name__)


def _solve(ball: Ball, cushion: Cushion) -> tuple[Ball, Cushion]:
    rvw = ball.state.rvw.copy()

    logger.debug(f"v={rvw[1]}, w={rvw[2]}")

    normal_direction = cushion.get_normal_xy(ball.xyz)
    normal_direction = (
        -normal_direction
        if np.dot(normal_direction, ball.state.rvw[1]) > 0
        else normal_direction
    )

    relative_contact_velocity = ptmath.surface_velocity(
        rvw, -normal_direction, ball.params.R
    )

    v_n_0, v_t_0, tangent_direction = ptmath.decompose_normal_tangent(
        relative_contact_velocity, normal_direction, True
    )

    logger.debug(f"v_c_0={relative_contact_velocity}")
    logger.debug(f"n={normal_direction}, t={tangent_direction}")
    logger.debug(f"v_n_0={v_n_0}, v_t_0={v_t_0}")

    # inverse inertia matrix coefficients for sphere half-space collision
    effective_mass = ball.params.m
    beta_t = 3.5
    beta_n = 1.0
    beta_t_by_beta_n = beta_t / beta_n

    v_t_f, v_n_f = resolve_collinear_compliant_frictional_inelastic_collision(
        v_t_0=v_t_0,
        v_n_0=v_n_0,
        m=effective_mass,
        beta_t=beta_t,
        beta_n=beta_n,
        mu=ball.params.f_c,
        e_n=ball.params.e_c,
        k_n=1e3,  # TODO: cushion params
        eta_squared=(beta_t_by_beta_n / 1.7**2),  # TODO: cushion params
    )

    Dv_n = (v_n_f - v_n_0) / beta_n
    rvw[1] += Dv_n * normal_direction

    Dv_t = (v_t_f - v_t_0) / beta_t
    rvw[1] += Dv_t * tangent_direction
    rvw[2] += (2.5 / ball.params.R) * ptmath.cross(
        -normal_direction, Dv_t * tangent_direction
    )

    logger.debug(f"v_n_f={v_n_f}, v_t_f={v_t_f}")
    logger.debug(f"Dv_n={Dv_n}, Dv_t={Dv_t}")

    # Calculate final relative contact velocity from stronge output (`v_n_f` and `v_t_f`)
    # and from `rvw` which was modified based on stronge output,
    # then verify that they're equal
    v_c_f = v_n_f * normal_direction + v_t_f * tangent_direction
    relative_contact_velocity_f = ptmath.surface_velocity(
        rvw, -normal_direction, ball.params.R
    )
    logger.debug(f"v_c_f={v_c_f}")
    assert np.allclose(v_c_f, relative_contact_velocity_f), (
        f"v_c_f={v_c_f}, relative_contact_velocity_f={relative_contact_velocity_f}"
    )

    # FIXME-3D: add z-velocity back in
    rvw[1][2] = 0.0

    ball.state = BallState(rvw, const.sliding)

    return ball, cushion


@attrs.define
class StrongeCompliantLinear(CoreBallLCushionCollision):
    model: BallLCushionModel = attrs.field(
        default=BallLCushionModel.STRONGE_COMPLIANT, init=False, repr=False
    )

    def solve(
        self, ball: Ball, cushion: LinearCushionSegment
    ) -> tuple[Ball, LinearCushionSegment]:
        return _solve(ball, cushion)


@attrs.define
class StrongeCompliantCircular(CoreBallCCushionCollision):
    model: BallCCushionModel = attrs.field(
        default=BallCCushionModel.STRONGE_COMPLIANT, init=False, repr=False
    )

    def solve(
        self, ball: Ball, cushion: CircularCushionSegment
    ) -> tuple[Ball, CircularCushionSegment]:
        return _solve(ball, cushion)
