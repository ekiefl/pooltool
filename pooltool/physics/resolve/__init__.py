from __future__ import annotations

from typing import Protocol, Tuple

import attrs

from pooltool.events.datatypes import EventType
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.table.components import (
    CircularCushionSegment,
    LinearCushionSegment,
)
from pooltool.physics.resolve.ball_ball import BALL_BALL_DEFAULT
from pooltool.physics.resolve.ball_cushion import (
    BALL_CIRCULAR_CUSHION_DEFAULT,
    BALL_LINEAR_CUSHION_DEFAULT,
)
from pooltool.physics.resolve.transition import TRANSITION_DEFAULT


class BallBallCollisionStrategy(Protocol):
    def resolve(
        self, ball1: Ball, ball2: Ball, inplace: bool = False
    ) -> Tuple[Ball, Ball]:
        ...


class BallTransitionStrategy(Protocol):
    def resolve(self, ball: Ball, transition: EventType, inplace: bool = False) -> Ball:
        ...


class BallLinearCushionCollisionStrategy(Protocol):
    def resolve(
        self, ball: Ball, cushion: LinearCushionSegment, inplace: bool = False
    ) -> Tuple[Ball, LinearCushionSegment]:
        ...


class BallCircularCushionCollisionStrategy(Protocol):
    def resolve(
        self, ball: Ball, cushion: CircularCushionSegment, inplace: bool = False
    ) -> Tuple[Ball, CircularCushionSegment]:
        ...


@attrs.define
class Resolver:
    ball_ball: BallBallCollisionStrategy
    ball_linear_cushion: BallLinearCushionCollisionStrategy
    ball_circular_cushion: BallCircularCushionCollisionStrategy
    transition: BallTransitionStrategy

    @classmethod
    def default(cls) -> Resolver:
        return Resolver(
            ball_ball=BALL_BALL_DEFAULT,
            ball_linear_cushion=BALL_LINEAR_CUSHION_DEFAULT,
            ball_circular_cushion=BALL_CIRCULAR_CUSHION_DEFAULT,
            transition=TRANSITION_DEFAULT,
        )
