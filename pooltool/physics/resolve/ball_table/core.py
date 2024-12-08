from abc import ABC, abstractmethod
from typing import Protocol, Tuple

from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.table.datatypes import Table


class _BaseStrategy(Protocol):
    def resolve(
        self, ball: Ball, table: Table, inplace: bool = False
    ) -> Tuple[Ball, Table]: ...


class BallTableCollisionStrategy(_BaseStrategy, Protocol):
    """Ball-table collision models must satisfy this protocol"""

    def solve(self, ball: Ball, table: Table) -> Tuple[Ball, Table]:
        """This method resolves a ball-table cushion collision"""
        ...


class CoreBallTableCollision(ABC):
    """Operations used by every ball-table collision resolver"""

    def resolve(
        self, ball: Ball, table: Table, inplace: bool = False
    ) -> Tuple[Ball, Table]:
        if not inplace:
            # The table state is invariant so doesn't need to be copied.
            ball = ball.copy()

        return self.solve(ball, table)

    @abstractmethod
    def solve(self, ball: Ball, table: Table) -> Tuple[Ball, Table]:
        pass
