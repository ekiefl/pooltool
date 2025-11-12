#! /usr/bin/env python
"""Event-based simulation introspection tools.

This module provides utilities for capturing and analyzing simulation state at each
step of event-based pool simulations. It enables detailed inspection of system states,
events, and collision caches throughout simulation execution.

The primary use case is debugging and understanding simulation behavior by examining:
- System state before evolution (pre_evolve)
- System state after time evolution but before collision resolution (post_evolve)
- System state after collision resolution (post_resolve)
- All prospective events considered at each step
- Collision and transition caches at each step

Key components:
    SimulationSnapshot: Captures complete state at a single simulation step
    SimulationSnapshotSequence: Collection of snapshots across entire simulation
    simulate_with_snapshots: Runs simulation while capturing snapshots
"""

from __future__ import annotations

from pathlib import Path

import attrs

from pooltool.events import (
    Event,
    EventType,
    ball_ball_collision,
    ball_circular_cushion_collision,
    ball_linear_cushion_collision,
    ball_pocket_collision,
    stick_ball_collision,
)
from pooltool.evolution.event_based.cache import CollisionCache, TransitionCache
from pooltool.evolution.event_based.config import INCLUDED_EVENTS
from pooltool.evolution.event_based.simulate import (
    DEFAULT_ENGINE,
    _SimulationState,
)
from pooltool.physics.engine import PhysicsEngine
from pooltool.serialize import conversion
from pooltool.serialize.serializers import Pathish
from pooltool.system.datatypes import System


def _get_collision_events_from_cache(
    system: System, cache: CollisionCache
) -> list[Event]:
    events = []

    if EventType.BALL_BALL in cache.times:
        for (ball1_id, ball2_id), time in cache.times[EventType.BALL_BALL].items():
            events.append(
                ball_ball_collision(
                    ball1=system.balls[ball1_id],
                    ball2=system.balls[ball2_id],
                    time=time,
                )
            )

    if EventType.BALL_LINEAR_CUSHION in cache.times:
        for (ball_id, cushion_id), time in cache.times[
            EventType.BALL_LINEAR_CUSHION
        ].items():
            events.append(
                ball_linear_cushion_collision(
                    ball=system.balls[ball_id],
                    cushion=system.table.cushion_segments.linear[cushion_id],
                    time=time,
                )
            )

    if EventType.BALL_CIRCULAR_CUSHION in cache.times:
        for (ball_id, cushion_id), time in cache.times[
            EventType.BALL_CIRCULAR_CUSHION
        ].items():
            events.append(
                ball_circular_cushion_collision(
                    ball=system.balls[ball_id],
                    cushion=system.table.cushion_segments.circular[cushion_id],
                    time=time,
                )
            )

    if EventType.BALL_POCKET in cache.times:
        for (ball_id, pocket_id), time in cache.times[EventType.BALL_POCKET].items():
            events.append(
                ball_pocket_collision(
                    ball=system.balls[ball_id],
                    pocket=system.table.pockets[pocket_id],
                    time=time,
                )
            )

    if EventType.STICK_BALL in cache.times:
        for (cue_id, ball_id), time in cache.times[EventType.STICK_BALL].items():
            events.append(
                stick_ball_collision(
                    stick=system.cue,
                    ball=system.balls[ball_id],
                    time=time,
                )
            )

    return events


@attrs.define
class SimulationSnapshot:
    step_number: int
    system: System
    selected_event: Event
    collision_cache: CollisionCache
    transition_cache: TransitionCache
    engine: PhysicsEngine

    def get_prospective_events(self) -> list[Event]:
        """Get all prospective events.

        Returns all cached collision and transition events that were possible at the
        given step, sorted by time. These events are "prospective" - they have been
        detected but not yet resolved, so their agents' initial and final states are
        None.

        A prospective event becomes resolved when it is selected as the next event to
        occur and the physics engine processes it via resolver.resolve(), which sets
        the initial and final states of the agents involved.

        Args:
            step: The simulation step index

        Returns:
            A list of prospective events sorted by time
        """
        system = self.system
        cache = self.collision_cache
        transition_cache = self.transition_cache

        events = _get_collision_events_from_cache(system, cache)

        for event in transition_cache.transitions.values():
            events.append(event)

        return sorted(events, key=lambda e: e.time)

    def pre_evolve_system(self) -> System:
        """Returns a copy of the system state"""
        return self.system.copy()

    def post_evolve_system(self, event: Event) -> System:
        system = self.pre_evolve_system()
        dt = event.time - system.t
        _SimulationState.evolve(system, dt)
        system.t += dt
        return system

    def post_resolve_system(self, event: Event) -> System:
        system = self.post_evolve_system(event)
        self.engine.resolver.resolve(system, event)
        system._update_history(event)
        return system


@attrs.define
class SimulationSnapshotSequence:
    steps: list[SimulationSnapshot] = attrs.field(factory=list)
    engine: PhysicsEngine = attrs.field(factory=PhysicsEngine)

    def add(self, snapshot: SimulationSnapshot) -> None:
        self.steps.append(snapshot)

    def __len__(self) -> int:
        return len(self.steps)

    def __getitem__(self, index: int) -> SimulationSnapshot:
        return self.steps[index]

    def save(self, path: Pathish) -> Path:
        path = Path(path)
        conversion.unstructure_to(self, path)
        return path

    @classmethod
    def load(cls, path: Pathish) -> SimulationSnapshotSequence:
        return conversion.structure_from(path, cls)


def simulate_with_snapshots(
    shot: System,
    output_path: Path | None = None,
    engine: PhysicsEngine | None = None,
    t_final: float | None = None,
    include: set[EventType] = INCLUDED_EVENTS,
    max_events: int = 0,
) -> tuple[System, SimulationSnapshotSequence]:
    if not engine:
        engine = DEFAULT_ENGINE

    sim = _SimulationState(
        shot.copy(),
        engine,
        t_final,
        include,
        max_events,
    )
    sim.init()

    snapshot_sequence = SimulationSnapshotSequence(engine=engine)

    step = 0
    while not sim.done:
        system_pre_evolve = sim.shot.copy()

        event = sim.step()

        # Capture the cache states when they have all possible event times for the
        # pre-evolve shot.
        collision_cache_snapshot = sim.collision_cache.copy()
        transition_cache_snapshot = sim.transition_cache.copy()

        if not sim.done:
            # Update the caches to be accurate for the next iteration.
            sim.update_caches(event)

        snapshot = SimulationSnapshot(
            step_number=step,
            system=system_pre_evolve,
            selected_event=event,
            collision_cache=collision_cache_snapshot,
            transition_cache=transition_cache_snapshot,
            engine=engine,
        )

        snapshot_sequence.add(snapshot)
        if output_path is not None:
            snapshot_sequence.save(output_path)

        step += 1

    return sim.shot, snapshot_sequence


if __name__ == "__main__":
    from pathlib import Path

    import pooltool as pt

    output = Path("test.json")
    simulate_with_snapshots(pt.System.example(), output)
    seq = SimulationSnapshotSequence.load(output)
    system = pt.simulate(pt.System.example())
