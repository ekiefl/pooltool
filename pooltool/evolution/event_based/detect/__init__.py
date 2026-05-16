from __future__ import annotations

import attrs

from pooltool.evolution.event_based.detect.stick_ball import (
    StickBallDetection,
    StickBallDetectionStrategy,
)


@attrs.define
class EventDetector:
    """Bundles per-event-type detection strategies.

    Fields are typed as the concrete strategy class rather than the corresponding
    ``*DetectionStrategy`` protocol. This keeps cattrs structuring trivial, but when a
    second implementation is added for a given event type, this field type should be
    widened (to the protocol with a registry + structure hook that dispatches on a tag,
    in the style of :class:`pooltool.physics.resolve.resolver.Resolver`).

    Attributes:
        stick_ball:
            Strategy for detecting the next stick-ball collision.
    """

    stick_ball: StickBallDetection = attrs.field(factory=StickBallDetection)

    @classmethod
    def default(cls) -> EventDetector:
        return cls()


__all__ = [
    "EventDetector",
    "StickBallDetection",
    "StickBallDetectionStrategy",
]
