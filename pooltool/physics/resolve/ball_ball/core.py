from abc import ABC, abstractmethod
from typing import Protocol, Tuple

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball


class _BaseStrategy(Protocol):
    def make_kiss(self, ball1: Ball, ball2: Ball) -> Tuple[Ball, Ball]: ...

    def resolve(
        self, ball1: Ball, ball2: Ball, inplace: bool = False
    ) -> Tuple[Ball, Ball]: ...


class BallBallCollisionStrategy(_BaseStrategy, Protocol):
    """Ball-ball collision models must satisfy this protocol"""

    def solve(self, ball1: Ball, ball2: Ball) -> Tuple[Ball, Ball]:
        """This method resolves a ball-ball collision"""
        ...


class CoreBallBallCollision(ABC):
    """Operations used by every ball-ball collision resolver"""

    def make_kiss(self, ball1: Ball, ball2: Ball) -> Tuple[Ball, Ball]:
        """Translate the balls so they are (almost) touching

        This makes a correction such that if the balls are not _exactly_ 2*R apart, they
        are moved equally along their line of centers such that they are. Then, to avoid
        downstream float precision round-off errors, a small epsilon of additional
        distance (constants.EPS_SPACE) is put between them, ensuring the balls are
        non-intersecting.
        """
        r1, r2 = ball1.state.rvw[0], ball2.state.rvw[0]
        n = ptmath.unit_vector(r2 - r1)

        correction = 2 * ball1.params.R - ptmath.norm3d(r2 - r1) + const.EPS_SPACE
        ball2.state.rvw[0] += correction / 2 * n
        ball1.state.rvw[0] -= correction / 2 * n

        return ball1, ball2

    def resolve(
        self, ball1: Ball, ball2: Ball, inplace: bool = False
    ) -> Tuple[Ball, Ball]:
        if not inplace:
            ball1 = ball1.copy()
            ball2 = ball2.copy()

        ball1, ball2 = self.make_kiss(ball1, ball2)

        return self.solve(ball1, ball2)

    @abstractmethod
    def solve(self, ball1: Ball, ball2: Ball) -> Tuple[Ball, Ball]:
        pass
