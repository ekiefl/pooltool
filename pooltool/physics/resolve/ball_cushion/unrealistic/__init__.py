"""An unrealistic ball-cushion model"""

from typing import Tuple, TypeVar

import attrs
import numpy as np

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.table.components import (
    CircularCushionSegment,
    LinearCushionSegment,
)
from pooltool.physics.resolve.ball_cushion.core import (
    CoreBallCCushionCollision,
    CoreBallLCushionCollision,
)
from pooltool.physics.resolve.models import BallCCushionModel, BallLCushionModel

Cushion = TypeVar("Cushion", LinearCushionSegment, CircularCushionSegment)


def _solve(
    ball: Ball, cushion: Cushion, restitution: bool = True
) -> Tuple[Ball, Cushion]:
    """Given ball and cushion, unrealistically reflect the ball's momentum

    Args:
        restitution:
            By default, the ball's momentum is reflected without loss. Set this to true
            if the ball's restitution coefficient should dampen the outgoing velocity.
    """
    rvw = ball.state.rvw

    # Two things about the normal:
    #   1) Cushions have a get_normal method that returns the normal. For linear
    #      cushions this is determined solely by it's geometry. For circular
    #      cushions, the normal is a function of the ball's position (specifically,
    #      it is the line connecting the ball's and cushion's centers). To retain
    #      symmetry between method calls, both linear and circular cushion segments
    #      accept `rvw` as a parameter
    #   2) The cushion normal is arbitrarily assigned to face either into the table
    #      or away from the table. That's my bad--a mishap during development that
    #      we're still living with the consequences of. The burden is that you must
    #      assign a convention. Here I opt to orient the normal so it points away
    #      from the playing surface.
    normal = cushion.get_normal(rvw)
    normal = normal if np.dot(normal, rvw[1]) > 0 else -normal

    # Rotate frame of reference to the cushion frame. The cushion frame is defined
    # by the cushion's normal vector (convention: points away from table) being
    # parallel with <1,0,0>.
    psi = ptmath.angle(normal)
    rvw_R = ptmath.coordinate_rotation(rvw.T, -psi).T

    # Reverse velocity component lying in normal direction
    rvw_R[1, 0] *= -1 * (1 if not restitution else ball.params.e_c)

    # Rotate frame of reference back to the table frame
    rvw = ptmath.coordinate_rotation(rvw_R.T, psi).T

    # Set the ball's rvw
    ball.state.rvw = rvw

    # You'll also want to set the motion state of the ball to sliding
    ball.state.s = const.sliding

    return ball, cushion


@attrs.define
class UnrealisticLinear(CoreBallLCushionCollision):
    restitution: bool = False
    model: BallLCushionModel = attrs.field(
        default=BallLCushionModel.UNREALISTIC, init=False, repr=False
    )

    def solve(
        self, ball: Ball, cushion: LinearCushionSegment
    ) -> Tuple[Ball, LinearCushionSegment]:
        return _solve(ball, cushion, self.restitution)


@attrs.define
class UnrealisticCircular(CoreBallCCushionCollision):
    restitution: bool = False
    model: BallCCushionModel = attrs.field(
        default=BallCCushionModel.UNREALISTIC, init=False, repr=False
    )

    def solve(
        self, ball: Ball, cushion: CircularCushionSegment
    ) -> Tuple[Ball, CircularCushionSegment]:
        return _solve(ball, cushion, self.restitution)
