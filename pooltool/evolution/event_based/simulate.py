#! /usr/bin/env python

from __future__ import annotations

import attrs
import numpy as np

import pooltool.physics.evolve as evolve
from pooltool.events import Event, EventType, null_event
from pooltool.evolution.continuous import continuize
from pooltool.evolution.engine import SimulationEngine
from pooltool.evolution.event_based.cache import CollisionCache, TransitionCache
from pooltool.evolution.event_based.config import INCLUDED_EVENTS
from pooltool.objects.ball.datatypes import BallState
from pooltool.system.datatypes import System

DEFAULT_ENGINE = SimulationEngine()


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
        event = self.engine.event_detector.get_next_event(
            self.shot,
            transition_cache=self.transition_cache,
            collision_cache=self.collision_cache,
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
