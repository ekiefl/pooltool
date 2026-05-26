import attrs
import numpy as np
from numpy.typing import NDArray

import pooltool.constants as const
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.table.components import (
    CircularCushionSegment,
    Cushion,
    LinearCushionSegment,
)
from pooltool.physics.dimensionality import Dim
from pooltool.physics.resolve.ball_cushion.core import (
    CoreBallCCushionCollision,
    CoreBallLCushionCollision,
)
from pooltool.physics.resolve.models import BallCCushionModel, BallLCushionModel
from pooltool.physics.resolve.sphere_half_space_collision import (
    resolve_sphere_half_space_collision,
)


# TODO: move to common place
def final_ball_motion_state(rvw: NDArray[np.float64]) -> int:
    return const.airborne if rvw[1, 2] != 0.0 else const.sliding


def _solve(ball: Ball, cushion: Cushion) -> NDArray[np.float64]:
    return resolve_sphere_half_space_collision(
        normal=cushion.get_normal_3d(ball.xyz),
        rvw=ball.state.rvw,
        R=ball.params.R,
        mu_k=ball.params.f_c,
        e=ball.params.e_c,
    )


@attrs.define
class ImpulseFrictionalInelasticLinear2D(CoreBallLCushionCollision):
    model: BallLCushionModel = attrs.field(
        default=BallLCushionModel.IMPULSE_FRICTIONAL_INELASTIC_2D,
        init=False,
        repr=False,
    )
    dim: Dim = attrs.field(default=Dim.TWO, init=False, repr=False)

    def solve(
        self, ball: Ball, cushion: LinearCushionSegment
    ) -> tuple[Ball, LinearCushionSegment]:
        ball.state.rvw = _solve(ball, cushion)
        ball.state.rvw[1, 2] = 0.0
        ball.state.s = const.sliding
        return ball, cushion


@attrs.define
class ImpulseFrictionalInelasticCircular2D(CoreBallCCushionCollision):
    model: BallCCushionModel = attrs.field(
        default=BallCCushionModel.IMPULSE_FRICTIONAL_INELASTIC_2D,
        init=False,
        repr=False,
    )
    dim: Dim = attrs.field(default=Dim.TWO, init=False, repr=False)

    def solve(
        self, ball: Ball, cushion: CircularCushionSegment
    ) -> tuple[Ball, CircularCushionSegment]:
        ball.state.rvw = _solve(ball, cushion)
        ball.state.rvw[1, 2] = 0.0
        ball.state.s = const.sliding
        return ball, cushion


@attrs.define
class ImpulseFrictionalInelasticLinear3D(CoreBallLCushionCollision):
    model: BallLCushionModel = attrs.field(
        default=BallLCushionModel.IMPULSE_FRICTIONAL_INELASTIC_3D,
        init=False,
        repr=False,
    )
    dim: Dim = attrs.field(default=Dim.THREE, init=False, repr=False)

    def solve(
        self, ball: Ball, cushion: LinearCushionSegment
    ) -> tuple[Ball, LinearCushionSegment]:
        ball.state.rvw = _solve(ball, cushion)
        ball.state.s = final_ball_motion_state(ball.state.rvw)
        return ball, cushion


@attrs.define
class ImpulseFrictionalInelasticCircular3D(CoreBallCCushionCollision):
    model: BallCCushionModel = attrs.field(
        default=BallCCushionModel.IMPULSE_FRICTIONAL_INELASTIC_3D,
        init=False,
        repr=False,
    )
    dim: Dim = attrs.field(default=Dim.THREE, init=False, repr=False)

    def solve(
        self, ball: Ball, cushion: CircularCushionSegment
    ) -> tuple[Ball, CircularCushionSegment]:
        ball.state.rvw = _solve(ball, cushion)
        ball.state.s = final_ball_motion_state(ball.state.rvw)
        return ball, cushion
