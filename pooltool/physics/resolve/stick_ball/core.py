from abc import ABC, abstractmethod
from typing import Protocol, Tuple

import numpy as np
from numpy.typing import NDArray

import pooltool.constants as const
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.cue.datatypes import Cue


def final_ball_motion_state(rvw: NDArray[np.float64], R: float) -> int:
    """Return the final (post-collision) motion state label.

    If the z-velocity is non-zero, it is considered airborne, otherwise it is sliding.

    Args:
        rvw: The outgoing state vector of the ball.
        R: The radius of the ball.

    Notes:
        - A universal final_ball_motion_state fn could be a good idea.
    """
    if rvw[1, 2] != 0.0:
        return const.airborne

    return const.sliding


class _BaseStrategy(Protocol):
    def resolve(
        self, cue: Cue, ball: Ball, inplace: bool = False
    ) -> Tuple[Cue, Ball]: ...


class StickBallCollisionStrategy(_BaseStrategy, Protocol):
    """Stick-ball collision models must satisfy this protocol"""

    def solve(self, cue: Cue, ball: Ball) -> Tuple[Cue, Ball]:
        """This method resolves a stick-ball collision"""
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
