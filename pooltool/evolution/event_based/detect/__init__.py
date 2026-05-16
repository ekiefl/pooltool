from __future__ import annotations

import attrs

from pooltool.evolution.event_based.detect.stick_ball import (
    StickBallDetection,
    StickBallDetectionStrategy,
)


@attrs.define
class EventDetector:
    """Bundles per-event-type detection strategies.

    Attributes:
        stick_ball:
            Strategy for detecting the next stick-ball collision.
    """

    stick_ball: StickBallDetectionStrategy = attrs.field(factory=StickBallDetection)

    @classmethod
    def default(cls) -> EventDetector:
        return cls()


__all__ = [
    "EventDetector",
    "StickBallDetection",
    "StickBallDetectionStrategy",
]
