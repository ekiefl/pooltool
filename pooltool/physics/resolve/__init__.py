from __future__ import annotations

from typing import Protocol, Tuple

import attrs

from pooltool.events.datatypes import EventType
from pooltool.objects.ball.datatypes import Ball
from pooltool.physics.resolve.ball_ball import BALL_BALL_DEFAULT
from pooltool.physics.resolve.transition import TRANSITION_DEFAULT


class BallBallCollisionStrategy(Protocol):
    def resolve(
        self, ball1: Ball, ball2: Ball, inplace: bool = False
    ) -> Tuple[Ball, Ball]:
        ...


class BallTransitionStrategy(Protocol):
    def resolve(self, ball: Ball, transition: EventType, inplace: bool = False) -> Ball:
        ...


@attrs.define
class Resolver:
    ball_ball: BallBallCollisionStrategy
    transition: BallTransitionStrategy

    @classmethod
    def default(cls) -> Resolver:
        return Resolver(
            ball_ball=BALL_BALL_DEFAULT,
            transition=TRANSITION_DEFAULT,
        )
