"""An unrealistic ball-cushion model"""

from typing import Tuple

import attrs

from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.table.components import LinearCushionSegment
from pooltool.physics.resolve.ball_cushion.core import CoreBallLCushionCollision
from pooltool.physics.resolve.models import BallLCushionModel


@attrs.define
class UnrealisticLinear(CoreBallLCushionCollision):
    model: BallLCushionModel = attrs.field(
        default=BallLCushionModel.UNREALISTIC, init=False, repr=False
    )

    def solve(
        self, ball: Ball, cushion: LinearCushionSegment
    ) -> Tuple[Ball, LinearCushionSegment]:
        return ball, cushion
