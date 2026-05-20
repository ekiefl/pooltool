from __future__ import annotations

import attrs
import numpy as np

import pooltool.ptmath as ptmath
from pooltool.events import Event, EventType, null_event
from pooltool.evolution.event_based.cache import CollisionCache, TransitionCache
from pooltool.evolution.event_based.detect.ball_ball import (
    get_next_ball_ball_2d_event,
    get_next_ball_ball_3d_event,
)
from pooltool.evolution.event_based.detect.ball_cushion import (
    get_next_ball_circular_cushion_event,
    get_next_ball_linear_cushion_event,
)
from pooltool.evolution.event_based.detect.ball_pocket import (
    get_next_ball_pocket_event,
)
from pooltool.evolution.event_based.detect.ball_table import (
    get_next_ball_table_event,
)
from pooltool.evolution.event_based.detect.stick_ball import (
    get_next_stick_ball_event,
)
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
        energy = get_ball_energy(
            ball.state.rvw, ball.params.R, ball.params.m, ball.params.g
        )
        return (2, energy)

    if event_type.is_transition():
        ball_id = event.ids[0]
        ball = shot.balls[ball_id]
        energy = get_ball_energy(
            ball.state.rvw, ball.params.R, ball.params.m, ball.params.g
        )
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
        energy = get_ball_energy(
            ball.state.rvw, ball.params.R, ball.params.m, ball.params.g
        )
        return (3, energy)

    # TODO: tier and energy choice for BALL_TABLE has not been well thought
    # through or tested. Mirroring the cushion-collision semantics, but
    # BALL_TABLE-vs-other ties only become real once 3D activation lands and
    # airborne balls actually arise. Revisit once break / aerial trajectories
    # exercise this path.
    if event_type == EventType.BALL_TABLE:
        ball_id = event.ids[0]
        ball = shot.balls[ball_id]
        energy = get_ball_energy(
            ball.state.rvw, ball.params.R, ball.params.m, ball.params.g
        )
        return (3, energy)

    return (99, 0.0)


@attrs.define
class EventDetector:
    """Orchestrates per-event-type detection.

    The 2D-vs-3D branching for forked event types happens here, in ``get_next_event``.
    The per-event-type ``get_next_*_event`` functions are each mode-pure.

    Attributes:
        is_3d:
            Whether to dispatch to 3D detection variants. Set by ``SimulationEngine`` at
            construction.
    """

    is_3d: bool = False

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

        # Stick-ball collisions only occur at t=0 (shot initiation), so we skip
        # this check after the first timestep as an optimization. Other collision
        # types are always checked because they can occur at any time during
        # simulation. Note: even at t=0, we still call the remaining detection
        # functions to fully populate the collision cache, which is needed by
        # debug/introspection tools.
        if shot.t == 0:
            candidates.append(get_next_stick_ball_event(shot, collision_cache))

        candidates.append(transition_cache.get_next())
        candidates.append(get_next_ball_linear_cushion_event(shot, collision_cache))
        candidates.append(get_next_ball_circular_cushion_event(shot, collision_cache))
        candidates.append(get_next_ball_pocket_event(shot, collision_cache))

        if self.is_3d:
            candidates.append(get_next_ball_ball_3d_event(shot, collision_cache))
            candidates.append(get_next_ball_table_event(shot, collision_cache))
        else:
            candidates.append(get_next_ball_ball_2d_event(shot, collision_cache))

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
