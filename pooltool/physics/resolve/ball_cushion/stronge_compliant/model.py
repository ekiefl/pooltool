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


def _solve(ball: Ball, cushion: Cushion, omega_ratio: float) -> tuple[Ball, Cushion]:
    rvw = ball.state.rvw.copy()

    logger.debug(f"v={rvw[1]}, w={rvw[2]}")

    normal_direction = cushion.get_normal_3d(ball.xyz)
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
        k_n=1e3,  # arbitrary: collision outcome depends only on omega_ratio, not k_n.
        eta_squared=(beta_t_by_beta_n / omega_ratio**2),
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
    """Ball-cushion collision resolver using Stronge's compliant collision model.

    This model accounts for the compliant (spring-like) nature of cushion deformation
    during collision.

    Attributes:
        omega_ratio:
            Frequency ratio omega_t/omega_n controlling collision compliance, must be in
            range (1, 2). Higher values = stiffer cushion, lower values = softer.

    Notes:
        Architecturally, omega_ratio represents a cushion material property (Poisson's
        ratio) and should ideally be a cushion attribute rather than a model parameter.
        However, it is exposed here as a model parameter for pragmatic reasons. First,
        omega_ratio is intuitive to adjust. It ranges from [1, 2] and controls the
        frequency ratio omega_t/omega_n in the collision dynamics equations. This is the
        first model requiring cushion material properties, so we defer adding cushion
        attributes until needed by multiple models.

        Migration Path to Cushion Properties:
            When cushion material properties are added to cushion segments:
            1. Add ``poisson_ratio: float`` attribute to Linear/CircularCushionSegment
            2. Add ``youngs_modulus: float``` (k_n) if collision duration is needed
            3. Use ``omega_ratio_from_poisson_ratio()`` to convert
            4. Deprecate omega_ratio model parameter in favor of cushion property

        See ``poisson_ratio_from_omega_ratio()`` and
        ``omega_ratio_from_poisson_ratio()`` in ``stronge_compliant.py`` for conversion
        utilities.
    """

    omega_ratio: float = 1.7
    model: BallLCushionModel = attrs.field(
        default=BallLCushionModel.STRONGE_COMPLIANT, init=False, repr=False
    )

    def solve(
        self, ball: Ball, cushion: LinearCushionSegment
    ) -> tuple[Ball, LinearCushionSegment]:
        return _solve(ball, cushion, self.omega_ratio)


@attrs.define
class StrongeCompliantCircular(CoreBallCCushionCollision):
    """See :class:`StrongeCompliantLinear`."""

    omega_ratio: float = 1.7
    model: BallCCushionModel = attrs.field(
        default=BallCCushionModel.STRONGE_COMPLIANT, init=False, repr=False
    )

    def solve(
        self, ball: Ball, cushion: CircularCushionSegment
    ) -> tuple[Ball, CircularCushionSegment]:
        return _solve(ball, cushion, self.omega_ratio)
