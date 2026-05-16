from __future__ import annotations

import attrs

from pooltool.evolution.event_based.detect.ball_ball import (
    BallBallDetection,
    BallBallDetectionStrategy,
)
from pooltool.evolution.event_based.detect.ball_cushion import (
    BallCCushionDetection,
    BallCCushionDetectionStrategy,
    BallLCushionDetection,
    BallLCushionDetectionStrategy,
)
from pooltool.evolution.event_based.detect.ball_pocket import (
    BallPocketDetection,
    BallPocketDetectionStrategy,
)
from pooltool.evolution.event_based.detect.stick_ball import (
    StickBallDetection,
    StickBallDetectionStrategy,
)


@attrs.define
class EventDetector:
    """Bundles per-event-type detection strategies.

    Fields are typed as the concrete strategy class rather than the corresponding
    ``*DetectionStrategy`` protocol. This keeps cattrs structuring trivial — cattrs
    can structure into a concrete attrs class natively but cannot resolve a Protocol
    without a discriminator. When a second implementation is added for a given event
    type, this field type should be widened (e.g. to a union of concrete classes, or
    to the protocol with a registry + structure hook that dispatches on a tag, in
    the style of :class:`pooltool.physics.resolve.resolver.Resolver`).

    Attributes:
        stick_ball:
            Strategy for detecting the next stick-ball collision.
        ball_ball:
            Strategy for detecting the next ball-ball collision.
        ball_linear_cushion:
            Strategy for detecting the next ball-vs-linear-cushion-segment collision.
        ball_circular_cushion:
            Strategy for detecting the next ball-vs-circular-cushion-segment collision.
        ball_pocket:
            Strategy for detecting the next ball-pocket collision.
    """

    stick_ball: StickBallDetection = attrs.field(factory=StickBallDetection)
    ball_ball: BallBallDetection = attrs.field(factory=BallBallDetection)
    ball_linear_cushion: BallLCushionDetection = attrs.field(
        factory=BallLCushionDetection
    )
    ball_circular_cushion: BallCCushionDetection = attrs.field(
        factory=BallCCushionDetection
    )
    ball_pocket: BallPocketDetection = attrs.field(factory=BallPocketDetection)

    @classmethod
    def default(cls) -> EventDetector:
        return cls()


__all__ = [
    "EventDetector",
    "BallBallDetection",
    "BallBallDetectionStrategy",
    "BallCCushionDetection",
    "BallCCushionDetectionStrategy",
    "BallLCushionDetection",
    "BallLCushionDetectionStrategy",
    "BallPocketDetection",
    "BallPocketDetectionStrategy",
    "StickBallDetection",
    "StickBallDetectionStrategy",
]
