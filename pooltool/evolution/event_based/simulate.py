#! /usr/bin/env python

from __future__ import annotations

import attrs
import numpy as np

import pooltool.physics.evolve as evolve
import pooltool.ptmath as ptmath
from pooltool.events import Event, EventType, null_event
from pooltool.evolution.continuous import continuize
from pooltool.evolution.engine import SimulationEngine
from pooltool.evolution.event_based.cache import CollisionCache, TransitionCache
from pooltool.evolution.event_based.config import INCLUDED_EVENTS
from pooltool.objects.ball.datatypes import BallState
from pooltool.physics.utils import get_ball_energy
from pooltool.system.datatypes import System

DEFAULT_ENGINE = SimulationEngine()


def get_event_priority(event: Event, shot: System) -> tuple[int, float]:
    """Compute priority for an event to resolve ties among simultaneous events.

    Returns a tuple (tier, energy) where:
    - Lower tier = higher priority
    - Higher energy = higher priority within the same tier

    Priority tiers:
    - Tier 1: STICK_BALL (always first)
    - Tier 2: Transitions and BALL_POCKET (can resolve without affecting others)
    - Tier 3: BALL_BALL and ball-cushion collisions

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

    return (99, 0.0)


@attrs.define
class _SimulationState:
    shot: System
    engine: SimulationEngine

    t_final: float | None = None
    include: set[EventType] = INCLUDED_EVENTS
    max_events: int = 0

    done: bool = attrs.field(init=False, default=False)
    num_events: int = attrs.field(init=False, default=0)
    collision_cache: CollisionCache = attrs.field(init=False)
    transition_cache: TransitionCache = attrs.field(init=False)

    def __attrs_post_init__(self) -> None:
        self.collision_cache = CollisionCache.create()
        self.transition_cache = TransitionCache.create(self.shot)

    def init(self) -> None:
        self.shot.reset_history()
        self.shot._update_history(null_event(time=0))

    def step(self) -> Event:
        event = get_next_event(
            self.shot,
            transition_cache=self.transition_cache,
            collision_cache=self.collision_cache,
            engine=self.engine,
        )

        if event.time == np.inf:
            self.shot._update_history(null_event(time=self.shot.t))
            self.done = True
            return event

        self.evolve(self.shot, event.time - self.shot.t)

        if event.event_type in self.include:
            self.engine.resolver.resolve(self.shot, event)

        self.shot._update_history(event)

        if self.t_final is not None and self.shot.t >= self.t_final:
            self.shot._update_history(null_event(time=self.shot.t))
            self.done = True

        if self.max_events > 0 and self.num_events > self.max_events:
            self.shot.stop_balls()
            self.shot._update_history(null_event(time=self.shot.t))
            self.done = True

        self.num_events += 1

        return event

    def update_caches(self, event: Event) -> None:
        if event.event_type in self.include:
            self.transition_cache.update(event)
            self.collision_cache.invalidate(event)

    @staticmethod
    def evolve(shot: System, dt: float):
        """Evolves system an amount of time dt.

        FIXME This is very inefficent. each ball should store its natural trajectory
        thereby avoid a call to the clunky evolve_ball_motion. It could even be a
        partial function so parameters don't continuously need to be passed
        """

        for ball in shot.balls.values():
            rvw, _ = evolve.evolve_ball_motion(
                state=ball.state.s,
                rvw=ball.state.rvw,
                R=ball.params.R,
                m=ball.params.m,
                u_s=ball.params.u_s,
                u_sp=ball.params.u_sp,
                u_r=ball.params.u_r,
                g=ball.params.g,
                t=dt,
            )
            ball.state = BallState(rvw, ball.state.s, shot.t + dt)


def simulate(
    shot: System,
    engine: SimulationEngine | None = None,
    inplace: bool = False,
    continuous: bool = False,
    dt: float | None = None,
    t_final: float | None = None,
    include: set[EventType] = INCLUDED_EVENTS,
    max_events: int = 0,
) -> System:
    """Run a simulation on a system and return it

    Args:
        shot:
            The system you would like simulated. The system should already have energy,
            otherwise there will be nothing to simulate.
        engine:
            The engine holds all of the physics. You can instantiate your very own
            :class:`pooltool.evolution.SimulationEngine` object, or you can modify
            ``~/.config/pooltool/physics/resolver.json`` to change the default engine.
        inplace:
            By default, a copy of the passed system is simulated and returned. This
            leaves the passed system unmodified. If inplace is set to True, the passed
            system is modified in place, meaning no copy is made and the returned system
            is the passed system. For a more practical distinction, see Examples below.
        continuous:
            If True, the system will not only be simulated, but it will also be
            "continuized". This means each ball will be populated with a ball history
            with small fixed timesteps that make it ready for visualization.
        dt:
            The small fixed timestep used when continuous is True.
        t_final:
            If set, the simulation will end prematurely after the calculation of an
            event with ``event.time > t_final``.
        include:
            Which EventType are you interested in resolving? By default, all detected
            events are resolved.
        max_events:
            If this is greater than 0, and the shot has more than this many events, the
            simulation is stopped and the balls are set to stationary.

    Returns:
        System: The simulated system.

    Examples:
        Standard usage:

        >>> # Simulate a system
        >>> import pooltool as pt
        >>> system = pt.System.example()
        >>> simulated_system = pt.simulate(system)
        >>> assert not system.simulated
        >>> assert simulated_system.simulated

        The returned system is simulated, but the passed system remains unchanged.

        You can also modify the system in place:

        >>> # Simulate a system in place
        >>> import pooltool as pt
        >>> system = pt.System.example()
        >>> simulated_system = pt.simulate(system, inplace=True)
        >>> assert system.simulated
        >>> assert simulated_system.simulated
        >>> assert system is simulated_system

        Notice that the returned system _is_ the simulated system. Therefore, there is
        no point catching the return object when inplace is True:

        >>> # Simulate a system in place
        >>> import pooltool as pt
        >>> system = pt.System.example()
        >>> assert not system.simulated
        >>> pt.simulate(system, inplace=True)
        >>> assert system.simulated

        You can continuize the ball trajectories with `continuous`

        >>> # Simulate a system in place
        >>> import pooltool as pt
        >>> system = pt.simulate(pt.System.example(), continuous=True)
        >>> for ball in system.balls.values(): assert len(ball.history_cts) > 0

    See Also:
        - :func:`pooltool.evolution.continuize`
    """
    if not inplace:
        shot = shot.copy()

    if not engine:
        engine = DEFAULT_ENGINE

    sim = _SimulationState(shot, engine, t_final, include, max_events)
    sim.init()

    while not sim.done:
        event = sim.step()
        if not sim.done:
            sim.update_caches(event)

    if continuous:
        continuize(sim.shot, dt=0.01 if dt is None else dt, inplace=True)

    return sim.shot


def get_next_event(
    shot: System,
    *,
    transition_cache: TransitionCache | None = None,
    collision_cache: CollisionCache | None = None,
    engine: SimulationEngine = DEFAULT_ENGINE,
) -> Event:
    # If not passed, unpopulated caches are initialized to pass to delegate functions.
    # These empty caches will be populated by the delegate functions, but then thrown
    # away when this function returns.
    if transition_cache is None:
        transition_cache = TransitionCache.create(shot)
    if collision_cache is None:
        collision_cache = CollisionCache.create()

    # Collect all candidate events from each detection function.
    candidates: list[Event] = []

    # Stick-ball collisions only occur at t=0 (shot initiation), so we skip this
    # check after the first timestep as an optimization. Other collision types are
    # always checked because they can occur at any time during simulation. Note: even
    # at t=0, we still call the remaining detection functions to fully populate the
    # collision cache, which is needed by debug/introspection tools.
    if shot.t == 0:
        candidates.append(
            engine.event_detector.stick_ball.get_next(shot, collision_cache)
        )

    candidates.append(transition_cache.get_next())
    candidates.append(engine.event_detector.ball_ball.get_next(shot, collision_cache))
    candidates.append(
        engine.event_detector.ball_circular_cushion.get_next(shot, collision_cache)
    )
    candidates.append(
        engine.event_detector.ball_linear_cushion.get_next(shot, collision_cache)
    )
    candidates.append(engine.event_detector.ball_pocket.get_next(shot, collision_cache))

    # Find the earliest time among all candidates.
    min_time = min(event.time for event in candidates)

    if min_time == np.inf:
        return null_event(time=np.inf)

    # Filter to only events occurring at the earliest time.
    simultaneous = [e for e in candidates if e.time == min_time]

    if len(simultaneous) == 1:
        return simultaneous[0]

    # When multiple events occur at the same time, select by priority tier, then by
    # energy within the tier (higher energy first).
    def sort_key(e: Event) -> tuple[int, float]:
        tier, energy = get_event_priority(e, shot)
        return (tier, -energy)

    return min(simultaneous, key=sort_key)
