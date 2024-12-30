from abc import ABC, abstractmethod
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

import pooltool.constants as const
from pooltool.objects.ball.datatypes import Ball
from pooltool.physics.utils import on_table, rel_velocity
from pooltool.ptmath.utils import norm2d, norm3d


def bounce_height(vz: float, g: float) -> float:
    """Return how high a ball with outgoing positive z-velocity will bounce.

    Measured as distance from table to bottom of ball.
    """
    return 0.5 * vz**2 / g


def final_ball_motion_state(rvw: NDArray[np.float64], R: float) -> int:
    """Return the final (post-collision) motion state label."""
    if rvw[0, 2] < 0:
        return const.pocketed

    if rvw[1, 2] != 0.0 or not on_table(rvw, R):
        return const.airborne

    # On table with zero z-velocity

    if norm3d(rel_velocity(rvw, R)) > const.EPS:
        return const.sliding

    if norm2d(rvw[1]) > const.EPS:
        return const.rolling

    # Ball is non-translating

    if rvw[2, 2] != 0.0:
        return const.spinning

    return const.stationary


class _BaseStrategy(Protocol):
    def resolve(self, ball: Ball, inplace: bool = False) -> Ball: ...

    def make_kiss(self, ball: Ball) -> Ball: ...


class BallTableCollisionStrategy(_BaseStrategy, Protocol):
    """Ball-table collision models must satisfy this protocol"""

    def solve(self, ball: Ball) -> Ball:
        """This method resolves a ball-table cushion collision"""
        ...


class CoreBallTableCollision(ABC):
    """Operations used by every ball-table collision resolver"""

    def make_kiss(self, ball: Ball) -> Ball:
        """Translate the ball so its height is exactly its radius.

        This makes a correction such that if the ball is not at a height R, it is moved
        vertical such that it is.
        """
        ball.state.rvw[0, 2] = ball.params.R
        return ball

    def resolve(self, ball: Ball, inplace: bool = False) -> Ball:
        if not inplace:
            ball = ball.copy()

        ball = self.make_kiss(ball)
        return self.solve(ball)

    @abstractmethod
    def solve(self, ball: Ball) -> Ball:
        pass
