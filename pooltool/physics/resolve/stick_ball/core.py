from abc import ABC, abstractmethod
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

import pooltool.constants as const
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.cue.datatypes import Cue
from pooltool.physics.dimensionality import Dim


def final_ball_motion_state(rvw: NDArray[np.float64], R: float) -> int:
    """Return the final (post-strike) motion state label.

    If the z-velocity is non-zero the ball is considered airborne, otherwise
    it is sliding (a struck ball is always kinetic).

    Notes:
        - A universal ``final_ball_motion_state`` fn could be a good idea.
    """
    if rvw[1, 2] != 0.0:
        return const.airborne

    return const.sliding


class _BaseStrategy(Protocol):
    def resolve(
        self, cue: Cue, ball: Ball, inplace: bool = False
    ) -> tuple[Cue, Ball]: ...


class StickBallCollisionStrategy(_BaseStrategy, Protocol):
    """Stick-ball collision models must satisfy this protocol"""

    dim: Dim

    def solve(self, cue: Cue, ball: Ball) -> tuple[Cue, Ball]:
        """This method resolves a ball-circular cushion collision"""
        ...


class CoreStickBallCollision(ABC):
    """Operations used by every stick-ball collision resolver"""

    def resolve(self, cue: Cue, ball: Ball, inplace: bool = False) -> tuple[Cue, Ball]:
        if not inplace:
            cue = cue.copy()
            ball = ball.copy()

        return self.solve(cue, ball)

    @abstractmethod
    def solve(self, cue: Cue, ball: Ball) -> tuple[Cue, Ball]:
        pass
