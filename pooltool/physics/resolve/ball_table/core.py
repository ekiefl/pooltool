from abc import ABC, abstractmethod
from typing import Protocol

from pooltool.objects.ball.datatypes import Ball


class _BaseStrategy(Protocol):
    def resolve(self, ball: Ball, inplace: bool = False) -> Ball: ...


class BallTableCollisionStrategy(_BaseStrategy, Protocol):
    """Ball-table collision models must satisfy this protocol"""

    def solve(self, ball: Ball) -> Ball:
        """This method resolves a ball-table cushion collision"""
        ...


class CoreBallTableCollision(ABC):
    """Operations used by every ball-table collision resolver"""

    def resolve(self, ball: Ball, inplace: bool = False) -> Ball:
        if not inplace:
            ball = ball.copy()

        return self.solve(ball)

    @abstractmethod
    def solve(self, ball: Ball) -> Ball:
        pass