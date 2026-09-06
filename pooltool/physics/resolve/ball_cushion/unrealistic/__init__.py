"""An unrealistic ball-cushion model"""

import attrs

import pooltool.constants as const
import pooltool.ptmath as ptmath
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


def _solve(
    ball: Ball, cushion: Cushion, restitution: bool = True
) -> tuple[Ball, Cushion]:
    """Given ball and cushion, unrealistically reflect the ball's momentum

    Args:
        restitution:
            By default, the ball's momentum is reflected without loss. Set this to true
            if the ball's restitution coefficient should dampen the outgoing velocity.
    """
    rvw = ball.state.rvw

    # get_normal_xy points from the cushion toward the ball. Here the convention is
    # for the normal to point away from the playing surface, hence the negation.
    normal = -cushion.get_normal_xy(ball.xyz)

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
    dim: Dim = attrs.field(default=Dim.TWO, init=False, repr=False)

    def solve(
        self, ball: Ball, cushion: LinearCushionSegment
    ) -> tuple[Ball, LinearCushionSegment]:
        return _solve(ball, cushion, self.restitution)


@attrs.define
class UnrealisticCircular(CoreBallCCushionCollision):
    restitution: bool = False
    model: BallCCushionModel = attrs.field(
        default=BallCCushionModel.UNREALISTIC, init=False, repr=False
    )
    dim: Dim = attrs.field(default=Dim.TWO, init=False, repr=False)

    def solve(
        self, ball: Ball, cushion: CircularCushionSegment
    ) -> tuple[Ball, CircularCushionSegment]:
        return _solve(ball, cushion, self.restitution)
