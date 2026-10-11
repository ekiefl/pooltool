from abc import ABC, abstractmethod
from typing import Protocol

from pooltool.objects.ball.datatypes import Ball


class _BaseStrategy(Protocol):
    def resolve(self, ball: Ball, inplace: bool = False) -> Ball: ...


class BallOffTableCollisionStrategy(_BaseStrategy, Protocol):
    """Ball-off-table collision models must satisfy this protocol.

    Like :class:`pooltool.physics.resolve.ball_table.BallTableCollisionStrategy`,
    this protocol does not declare a ``dim`` attribute: only airborne balls leave the
    table, so the event has no meaning in 2D.
    """

    def solve(self, ball: Ball) -> Ball:
        """Resolves a ball-off-table collision"""
        ...


class CoreBallOffTableCollision(ABC):
    """Operations used by every ball-off-table collision resolver"""

    def resolve(self, ball: Ball, inplace: bool = False) -> Ball:
        if not inplace:
            ball = ball.copy()

        return self.solve(ball)

    @abstractmethod
    def solve(self, ball: Ball) -> Ball:
        pass
