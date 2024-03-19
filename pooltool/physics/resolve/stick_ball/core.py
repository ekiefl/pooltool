from abc import ABC, abstractmethod
from typing import Protocol, Tuple

from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.cue.datatypes import Cue


class _BaseStrategy(Protocol):
    def resolve(
        self, cue: Cue, ball: Ball, inplace: bool = False
    ) -> Tuple[Cue, Ball]: ...


class StickBallCollisionStrategy(_BaseStrategy, Protocol):
    """Stick-ball collision models must satisfy this protocol"""

    def solve(self, cue: Cue, ball: Ball) -> Tuple[Cue, Ball]:
        """This method resolves a ball-circular cushion collision"""
        ...


class CoreStickBallCollision(ABC):
    """Operations used by every stick-ball collision resolver"""

    def resolve(self, cue: Cue, ball: Ball, inplace: bool = False) -> Tuple[Cue, Ball]:
        if not inplace:
            cue = cue.copy()
            ball = ball.copy()

        return self.solve(cue, ball)

    @abstractmethod
    def solve(self, cue: Cue, ball: Ball) -> Tuple[Cue, Ball]:
        pass
