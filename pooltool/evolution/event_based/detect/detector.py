from __future__ import annotations

import attrs
import numpy as np

import pooltool.ptmath as ptmath
from pooltool.events import Event, EventType, null_event
from pooltool.evolution.event_based.cache import CollisionCache, TransitionCache
from pooltool.evolution.event_based.detect.ball_ball import BallBallDetection
from pooltool.evolution.event_based.detect.ball_cushion import (
    BallCCushionDetection,
    BallLCushionDetection,
)
from pooltool.evolution.event_based.detect.ball_pocket import BallPocketDetection
from pooltool.evolution.event_based.detect.ball_table import BallTableDetection
from pooltool.evolution.event_based.detect.stick_ball import StickBallDetection
from pooltool.physics.utils import get_ball_energy
from pooltool.system.datatypes import System


def _get_event_priority(event: Event, shot: System) -> tuple[int, float]:
    """Compute priority for an event to resolve ties among simultaneous events.

    Returns a tuple (tier, energy) where:
    - Lower tier = higher priority
    - Higher energy = higher priority within the same tier

    Priority tiers:
    - Tier 1: STICK_BALL (always first)
    - Tier 2: Transitions and BALL_POCKET (can resolve without affecting others)
    - Tier 3: BALL_BALL, ball-cushion collisions, and BALL_TABLE

    Args:
        event: The event to compute priority for.
        shot: The system state at the time the event was detected.

    Returns:
        A tuple of (tier, energy) for sorting.
    """
    event_type = event.event_type

    if event_type == EventType.NONE:
        return (99, 0.0)

    if event_type == EventType.STICK_BALL:
        return (1, shot.cue.V0**2)

    if event_type == EventType.BALL_POCKET:
        ball_id = event.ids[0]
        ball = shot.balls[ball_id]
        energy = get_ball_energy(ball.state.rvw, ball.params.R, ball.params.m)
        return (2, energy)

    if event_type.is_transition():
        ball_id = event.ids[0]
        ball = shot.balls[ball_id]
        energy = get_ball_energy(ball.state.rvw, ball.params.R, ball.params.m)
        return (2, energy)

    if event_type == EventType.BALL_BALL:
        ball1_id, ball2_id = event.ids
        v1 = shot.balls[ball1_id].state.rvw[1]
        v2 = shot.balls[ball2_id].state.rvw[1]
        energy = ptmath.squared_norm3d(v1 - v2)
        return (3, energy)

    if event_type in (EventType.BALL_LINEAR_CUSHION, EventType.BALL_CIRCULAR_CUSHION):
        ball_id = event.ids[0]
        ball = shot.balls[ball_id]
        energy = get_ball_energy(ball.state.rvw, ball.params.R, ball.params.m)
        return (3, energy)

    # TODO: tier and energy choice for BALL_TABLE has not been well thought
    # through or tested. Mirroring the cushion-collision semantics, but
    # BALL_TABLE-vs-other ties only become real once 3D activation lands and
    # airborne balls actually arise. Revisit once break / aerial trajectories
    # exercise this path.
    if event_type == EventType.BALL_TABLE:
        ball_id = event.ids[0]
        ball = shot.balls[ball_id]
        energy = get_ball_energy(ball.state.rvw, ball.params.R, ball.params.m)
        return (3, energy)

    return (99, 0.0)


@attrs.define
class EventDetector:
    """Bundles per-event-type detection strategies.

    Fields are typed as the concrete strategy class rather than the corresponding
    ``*DetectionStrategy`` protocol. This keeps cattrs structuring trivial — cattrs
    can structure into a concrete attrs class natively but cannot resolve a Protocol
    without a discriminator. When a second implementation is added for a given event
    type, this field type should be widened (e.g. to a union of concrete classes, or
    to the protocol with a registry + structure hook that dispatches on a tag, in
    the style of :class:`pooltool.physics.Resolver`).

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
        ball_table:
            Strategy for detecting the next ball-table collision (airborne ball
            landing on the table surface).
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
    ball_table: BallTableDetection = attrs.field(factory=BallTableDetection)

    @classmethod
    def default(cls) -> EventDetector:
        return cls()

    def get_next_event(
        self,
        shot: System,
        *,
        transition_cache: TransitionCache | None = None,
        collision_cache: CollisionCache | None = None,
    ) -> Event:
        """Return the soonest event across all event types.

        If multiple events occur at the same time, ties are broken by
        :func:`_get_event_priority`.
        """
        if transition_cache is None:
            transition_cache = TransitionCache.create(shot)
        if collision_cache is None:
            collision_cache = CollisionCache.create()

        candidates: list[Event] = []

        # Stick-ball collisions only occur at t=0 (shot initiation), so we skip this
        # check after the first timestep as an optimization. Other collision types are
        # always checked because they can occur at any time during simulation. Note:
        # even at t=0, we still call the remaining detection strategies to fully
        # populate the collision cache, which is needed by debug/introspection tools.
        if shot.t == 0:
            candidates.append(self.stick_ball.get_next(shot, collision_cache))

        candidates.append(transition_cache.get_next())
        candidates.append(self.ball_ball.get_next(shot, collision_cache))
        candidates.append(self.ball_circular_cushion.get_next(shot, collision_cache))
        candidates.append(self.ball_linear_cushion.get_next(shot, collision_cache))
        candidates.append(self.ball_pocket.get_next(shot, collision_cache))
        candidates.append(self.ball_table.get_next(shot, collision_cache))

        min_time = min(event.time for event in candidates)

        if min_time == np.inf:
            return null_event(time=np.inf)

        simultaneous = [e for e in candidates if e.time == min_time]

        if len(simultaneous) == 1:
            return simultaneous[0]

        def sort_key(e: Event) -> tuple[int, float]:
            tier, energy = _get_event_priority(e, shot)
            return (tier, -energy)

        return min(simultaneous, key=sort_key)
