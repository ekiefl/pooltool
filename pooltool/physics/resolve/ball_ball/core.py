from abc import ABC, abstractmethod
from typing import Protocol

import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball


class _BaseStrategy(Protocol):
    def make_kiss(self, ball1: Ball, ball2: Ball) -> tuple[Ball, Ball]: ...

    def resolve(
        self, ball1: Ball, ball2: Ball, inplace: bool = False
    ) -> tuple[Ball, Ball]: ...


class BallBallCollisionStrategy(_BaseStrategy, Protocol):
    """Ball-ball collision models must satisfy this protocol"""

    def solve(self, ball1: Ball, ball2: Ball) -> tuple[Ball, Ball]:
        """This method resolves a ball-ball collision"""
        ...


class CoreBallBallCollision(ABC):
    """Operations used by every ball-ball collision resolver"""

    def make_kiss(self, ball1: Ball, ball2: Ball) -> tuple[Ball, Ball]:
        """Translate the balls so they are (almost) touching

        Uses binary search to find a time offset that positions the balls at the target
        separation distance. The balls are moved equally along their line of centers
        (traced forward/backward in time along their velocity vectors) until they are
        separated by 2*R + spacer, where spacer is a small epsilon to avoid float
        precision errors.

        Args:
            ball1: First ball in the collision
            ball2: Second ball in the collision

        Returns:
            Modified ball1 and ball2 with adjusted positions
        """
        r1 = ball1.state.rvw[0]
        r2 = ball2.state.rvw[0]
        v1 = ball1.state.rvw[1]
        v2 = ball2.state.rvw[1]

        tmag = ball1.params.R / max(ptmath.norm3d(v1), ptmath.norm3d(v2))
        tmin = -tmag
        tmax = tmag

        spacer = 1e-12
        distance_target = 1e-15

        max_iter = 100
        for _ in range(max_iter):
            t = (tmin + tmax) / 2
            r1 = r1 - t * v1
            r2 = r2 - t * v2
            distance = ptmath.norm3d(r2 - r1)
            error = distance - (2 * ball1.params.R + spacer)

            if abs(error) < distance_target:
                break

            if error > 0:
                tmax = t
            else:
                tmin = t

        ball1.state.rvw[0] = r1
        ball2.state.rvw[0] = r2

        return ball1, ball2

    def resolve(
        self, ball1: Ball, ball2: Ball, inplace: bool = False
    ) -> tuple[Ball, Ball]:
        if not inplace:
            ball1 = ball1.copy()
            ball2 = ball2.copy()

        ball1, ball2 = self.make_kiss(ball1, ball2)

        return self.solve(ball1, ball2)

    @abstractmethod
    def solve(self, ball1: Ball, ball2: Ball) -> tuple[Ball, Ball]:
        pass
