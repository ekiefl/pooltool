from __future__ import annotations

from typing import Protocol, Tuple

import attrs

from pooltool.objects.ball.datatypes import Ball
from pooltool.physics.resolve.ball_ball import BALL_BALL_DEFAULT


class BallBallCollisionStrategy(Protocol):
    def resolve(
        self, ball1: Ball, ball2: Ball, inplace: bool = False
    ) -> Tuple[Ball, Ball]:
        ...


@attrs.define
class Resolver:
    ball_ball: BallBallCollisionStrategy

    @classmethod
    def default(cls) -> Resolver:
        return Resolver(
            ball_ball=BALL_BALL_DEFAULT,
        )
