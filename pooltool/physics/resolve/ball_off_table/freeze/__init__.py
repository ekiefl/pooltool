import attrs

import pooltool.constants as const
from pooltool.objects.ball.datatypes import Ball
from pooltool.physics.resolve.ball_off_table.core import CoreBallOffTableCollision
from pooltool.physics.resolve.models import BallOffTableModel


@attrs.define
class FreezeOffTable(CoreBallOffTableCollision):
    """Freeze the ball where it left the table.

    The position is kept, so the ball marks where it crossed the boundary. All
    momentum is discarded so the ball carries no energy into later shots, and the
    motion state becomes off-table, which takes part in no further physics.
    """

    model: BallOffTableModel = attrs.field(
        default=BallOffTableModel.FREEZE, init=False, repr=False
    )

    def solve(self, ball: Ball) -> Ball:
        ball.state.rvw[1, :] = [0.0, 0.0, 0.0]
        ball.state.rvw[2, :] = [0.0, 0.0, 0.0]
        ball.state.s = const.off_table
        return ball
