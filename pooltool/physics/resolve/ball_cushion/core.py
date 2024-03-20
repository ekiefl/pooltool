from abc import ABC, abstractmethod
from typing import Protocol, Tuple

import numpy as np

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.table.components import (
    CircularCushionSegment,
    LinearCushionSegment,
)


class _BaseLinearStrategy(Protocol):
    def make_kiss(self, ball: Ball, cushion: LinearCushionSegment) -> Ball: ...

    def resolve(
        self, ball: Ball, cushion: LinearCushionSegment, inplace: bool = False
    ) -> Tuple[Ball, LinearCushionSegment]: ...


class _BaseCircularStrategy(Protocol):
    def make_kiss(self, ball: Ball, cushion: CircularCushionSegment) -> Ball: ...

    def resolve(
        self, ball: Ball, cushion: CircularCushionSegment, inplace: bool = False
    ) -> Tuple[Ball, CircularCushionSegment]: ...


class BallLCushionCollisionStrategy(_BaseLinearStrategy, Protocol):
    """Ball-linear cushion collision models must satisfy this protocol"""

    def solve(
        self, ball: Ball, cushion: LinearCushionSegment
    ) -> Tuple[Ball, LinearCushionSegment]:
        """This method resolves a ball-circular cushion collision"""
        ...


class BallCCushionCollisionStrategy(_BaseCircularStrategy, Protocol):
    """Ball-circular cushion collision models must satisfy this protocol"""

    def solve(
        self, ball: Ball, cushion: CircularCushionSegment
    ) -> Tuple[Ball, CircularCushionSegment]:
        """This method resolves a ball-circular cushion collision"""
        ...


class CoreBallLCushionCollision(ABC):
    """Operations used by every ball-linear cushion collision resolver"""

    def make_kiss(self, ball: Ball, cushion: LinearCushionSegment) -> Ball:
        """Translate the ball so it (almost) touches the linear cushion segment

        This makes a correction such that if the ball is not a distance R from the
        cushion, the ball is moved along the normal such that it is. To avoid downstream
        float precision round-off error, a small epsilon of additional distance
        (constants.EPS_SPACE) is put between them, ensuring the cushion and ball are
        separated post-resolution.
        """
        normal = cushion.get_normal(ball.state.rvw)

        # orient the normal so it points away from playing surface
        normal = normal if np.dot(normal, ball.state.rvw[1]) > 0 else -normal

        # Calculate the point on cushion line where contact should be made, then set the
        # z-component to match the ball's height
        c = ptmath.point_on_line_closest_to_point(
            cushion.p1, cushion.p2, ball.state.rvw[0]
        )
        c[2] = ball.state.rvw[0, 2]

        # Move the ball to exactly meet the cushion
        correction = (
            ball.params.R - ptmath.norm3d(ball.state.rvw[0] - c) + const.EPS_SPACE
        )
        ball.state.rvw[0] -= correction * normal

        return ball

    def resolve(
        self, ball: Ball, cushion: LinearCushionSegment, inplace: bool = False
    ) -> Tuple[Ball, LinearCushionSegment]:
        if not inplace:
            ball = ball.copy()
            cushion = cushion.copy()

        ball = self.make_kiss(ball, cushion)

        return self.solve(ball, cushion)

    @abstractmethod
    def solve(
        self, ball: Ball, cushion: LinearCushionSegment
    ) -> Tuple[Ball, LinearCushionSegment]:
        pass


class CoreBallCCushionCollision(ABC):
    """Operations used by every ball-linear cushion collision resolver"""

    def make_kiss(self, ball: Ball, cushion: CircularCushionSegment) -> Ball:
        """Translate the ball so it (almost) touches the circular cushion segment

        This makes a correction such that if the ball is not a distance R from the
        cushion, the ball is moved along the normal such that it is. To avoid downstream
        float precision round-off error, a small epsilon of additional distance
        (constants.EPS_SPACE) is put between them, ensuring the cushion and ball are
        separated post-resolution.
        """
        normal = cushion.get_normal(ball.state.rvw)

        # orient the normal so it points away from playing surface
        normal = normal if np.dot(normal, ball.state.rvw[1]) > 0 else -normal

        c = np.array([cushion.center[0], cushion.center[1], ball.state.rvw[0, 2]])
        correction = (
            ball.params.R
            + cushion.radius
            - ptmath.norm3d(ball.state.rvw[0] - c)
            - const.EPS_SPACE
        )

        ball.state.rvw[0] += correction * normal

        return ball

    def resolve(
        self, ball: Ball, cushion: CircularCushionSegment, inplace: bool = False
    ) -> Tuple[Ball, CircularCushionSegment]:
        if not inplace:
            ball = ball.copy()
            cushion = cushion.copy()

        ball = self.make_kiss(ball, cushion)

        return self.solve(ball, cushion)  # type: ignore
