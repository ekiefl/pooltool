"""An unrealistic ball-cushion model"""

from typing import Tuple

from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.table.components import LinearCushionSegment
from pooltool.physics.resolve.ball_cushion.core import CoreBallLCushionCollision


class UnrealisticLinear(CoreBallLCushionCollision):
    def solve(
        self, ball: Ball, cushion: LinearCushionSegment
    ) -> Tuple[Ball, LinearCushionSegment]:
        return ball, cushion
