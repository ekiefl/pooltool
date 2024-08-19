#! /usr/bin/env python

from __future__ import annotations

from itertools import combinations
from typing import List, Optional, Set, Tuple, cast

import numpy as np

import pooltool.constants as const
import pooltool.physics.evolve as evolve
import pooltool.ptmath as ptmath
from pooltool.events import (
    Event,
    EventType,
    ball_ball_collision,
    ball_circular_cushion_collision,
    ball_linear_cushion_collision,
    ball_pocket_collision,
    null_event,
    stick_ball_collision,
)
from pooltool.evolution.continuize import continuize
from pooltool.evolution.event_based import solve
from pooltool.evolution.event_based.cache import CollisionCache, TransitionCache
from pooltool.evolution.event_based.config import INCLUDED_EVENTS
from pooltool.objects.ball.datatypes import Ball, BallState
from pooltool.objects.table.components import (
    CircularCushionSegment,
    LinearCushionSegment,
    Pocket,
)
from pooltool.physics.engine import PhysicsEngine
from pooltool.ptmath.roots.quartic import QuarticSolver, solve_quartics
from pooltool.system.datatypes import System

DEFAULT_ENGINE = PhysicsEngine()


def _evolve(shot: System, dt: float):
    """Evolves current ball an amount of time dt

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
    engine: Optional[PhysicsEngine] = None,
    inplace: bool = False,
    continuous: bool = False,
    dt: Optional[float] = None,
    t_final: Optional[float] = None,
    quartic_solver: QuarticSolver = QuarticSolver.HYBRID,
    include: Set[EventType] = INCLUDED_EVENTS,
    max_events: int = 0,
) -> System:
    """Run a simulation on a system and return it

    Args:
        shot:
            The system you would like simulated. The system should already have energy,
            otherwise there will be nothing to simulate.
        engine:
            The engine holds all of the physics. You can instantiate your very own
            :class:`pooltool.physics.engine.PhysicsEngine` object, or you can modify
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
        quartic_solver:
            Which QuarticSolver do you want to use for solving quartic polynomials?
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
        - :func:`pooltool.evolution.continuize.continuize`
    """
    if not inplace:
        shot = shot.copy()

    if not engine:
        engine = DEFAULT_ENGINE

    shot.reset_history()
    shot._update_history(null_event(time=0))

    if shot.get_system_energy() == 0 and shot.cue.V0 > 0:
        # System has no energy, but the cue stick has an impact velocity. So create and
        # resolve a stick-ball collision to start things off
        event = stick_ball_collision(
            stick=shot.cue,
            ball=shot.balls[shot.cue.cue_ball_id],
            time=0,
            set_initial=True,
        )
        engine.resolver.resolve(shot, event)
        shot._update_history(event)

    collision_cache = CollisionCache()
    transition_cache = TransitionCache.create(shot)

    events = 0
    while True:
        event = get_next_event(
            shot,
            transition_cache=transition_cache,
            collision_cache=collision_cache,
            quartic_solver=quartic_solver,
        )

        if event.time == np.inf:
            shot._update_history(null_event(time=shot.t))
            break

        _evolve(shot, event.time - shot.t)

        if event.event_type in include:
            engine.resolver.resolve(shot, event)
            transition_cache.update(event)
            collision_cache.invalidate(event)

        shot._update_history(event)

        if t_final is not None and shot.t >= t_final:
            shot._update_history(null_event(time=shot.t))
            break

        if max_events > 0 and events > max_events:
            shot.stop_balls()
            break

        events += 1

    if continuous:
        continuize(shot, dt=0.01 if dt is None else dt, inplace=True)

    return shot


def get_next_event(
    shot: System,
    *,
    transition_cache: Optional[TransitionCache] = None,
    collision_cache: Optional[CollisionCache] = None,
    quartic_solver: QuarticSolver = QuarticSolver.HYBRID,
) -> Event:
    # Start by assuming next event doesn't happen
    event = null_event(time=np.inf)

    if transition_cache is None:
        transition_cache = TransitionCache.create(shot)

    if collision_cache is None:
        collision_cache = CollisionCache()

    transition_event = transition_cache.get_next()
    if transition_event.time < event.time:
        event = transition_event

    ball_ball_event = get_next_ball_ball_collision(
        shot, collision_cache=collision_cache, solver=quartic_solver
    )
    if ball_ball_event.time < event.time:
        event = ball_ball_event

    ball_linear_cushion_event = get_next_ball_linear_cushion_collision(shot)
    if ball_linear_cushion_event.time < event.time:
        event = ball_linear_cushion_event

    ball_circular_cushion_event = get_next_ball_circular_cushion_event(
        shot, solver=quartic_solver
    )
    if ball_circular_cushion_event.time < event.time:
        event = ball_circular_cushion_event

    ball_pocket_event = get_next_ball_pocket_collision(shot, solver=quartic_solver)
    if ball_pocket_event.time < event.time:
        event = ball_pocket_event

    return event


def get_next_ball_ball_collision(
    shot: System,
    collision_cache: CollisionCache,
    solver: QuarticSolver = QuarticSolver.HYBRID,
) -> Event:
    """Returns next ball-ball collision"""

    ball_pairs: List[Tuple[str, str]] = []
    collision_coeffs: List[Tuple[float, ...]] = []

    cache = collision_cache.times.setdefault(EventType.BALL_BALL, {})

    for ball1, ball2 in combinations(shot.balls.values(), 2):
        ball_pair = (ball1.id, ball2.id)
        if ball_pair in cache:
            continue

        ball1_state = ball1.state
        ball1_params = ball1.params

        ball2_state = ball2.state
        ball2_params = ball2.params

        if ball1_state.s == const.pocketed or ball2_state.s == const.pocketed:
            cache[ball_pair] = np.inf
        elif (
            ball1_state.s in const.nontranslating
            and ball2_state.s in const.nontranslating
        ):
            cache[ball_pair] = np.inf
        elif (
            ptmath.norm3d(ball1_state.rvw[0] - ball2_state.rvw[0])
            < ball1_params.R + ball2_params.R
        ):
            # If balls are intersecting, avoid internal collisions
            cache[ball_pair] = np.inf
        else:
            ball_pairs.append(ball_pair)
            collision_coeffs.append(
                solve.ball_ball_collision_coeffs(
                    rvw1=ball1_state.rvw,
                    rvw2=ball2_state.rvw,
                    s1=ball1_state.s,
                    s2=ball2_state.s,
                    mu1=(
                        ball1_params.u_s
                        if ball1_state.s == const.sliding
                        else ball1_params.u_r
                    ),
                    mu2=(
                        ball2_params.u_s
                        if ball2_state.s == const.sliding
                        else ball2_params.u_r
                    ),
                    m1=ball1_params.m,
                    m2=ball2_params.m,
                    g1=ball1_params.g,
                    g2=ball2_params.g,
                    R=ball1_params.R,
                )
            )

    if len(collision_coeffs):
        roots = solve_quartics(ps=np.array(collision_coeffs), solver=solver)
        for root, ball_pair in zip(roots, ball_pairs, strict=True):
            cache[ball_pair] = shot.t + root

    # The cache is now populated and up-to-date

    # Let's be sure of it
    for ball1, ball2 in combinations(shot.balls.values(), 2):
        assert (
            ball1.id,
            ball2.id,
        ) in cache, f"{ball1.id}, {ball2.id} not in cache"

    # Let's be sure of it
    for ball1_id, ball2_id in cache:
        assert (
            cache[(ball1_id, ball2_id)] > shot.t
        ), f"{ball1_id}, {ball2_id} event time in past!"

    ball_pair = min(cache, key=lambda k: cast(float, cache.get(k)))

    return ball_ball_collision(
        ball1=shot.balls[ball_pair[0]],
        ball2=shot.balls[ball_pair[1]],
        time=cache[ball_pair],
    )


def get_next_ball_circular_cushion_event(
    shot: System, solver: QuarticSolver = QuarticSolver.HYBRID
) -> Event:
    """Returns next ball-cushion collision (circular cushion segment)"""

    dtau_E = np.inf
    agent_ids = []
    collision_coeffs = []

    for ball in shot.balls.values():
        if ball.state.s in const.nontranslating:
            continue

        state = ball.state
        params = ball.params

        for cushion in shot.table.cushion_segments.circular.values():
            collision_coeffs.append(
                solve.ball_circular_cushion_collision_coeffs(
                    rvw=state.rvw,
                    s=state.s,
                    a=cushion.a,
                    b=cushion.b,
                    r=cushion.radius,
                    mu=(params.u_s if state.s == const.sliding else params.u_r),
                    m=params.m,
                    g=params.g,
                    R=params.R,
                )
            )

            agent_ids.append((ball.id, cushion.id))

    if not len(collision_coeffs):
        # There are no collisions to test for
        return ball_circular_cushion_collision(
            Ball.dummy(), CircularCushionSegment.dummy(), shot.t + dtau_E
        )

    roots = solve_quartics(ps=np.array(collision_coeffs), solver=solver)
    dtau_E, index = roots.min(), roots.argmin()

    ball_id, cushion_id = agent_ids[index]
    ball, cushion = (
        shot.balls[ball_id],
        shot.table.cushion_segments.circular[cushion_id],
    )

    return ball_circular_cushion_collision(ball, cushion, shot.t + dtau_E)


def get_next_ball_linear_cushion_collision(shot: System) -> Event:
    """Returns next ball-cushion collision (linear cushion segment)"""

    dtau_E_min = np.inf
    involved_agents = (Ball.dummy(), LinearCushionSegment.dummy())

    for ball in shot.balls.values():
        if ball.state.s in const.nontranslating:
            continue

        state = ball.state
        params = ball.params

        for cushion in shot.table.cushion_segments.linear.values():
            dtau_E = solve.ball_linear_cushion_collision_time(
                rvw=state.rvw,
                s=state.s,
                lx=cushion.lx,
                ly=cushion.ly,
                l0=cushion.l0,
                p1=cushion.p1,
                p2=cushion.p2,
                direction=cushion.direction,
                mu=(params.u_s if state.s == const.sliding else params.u_r),
                m=params.m,
                g=params.g,
                R=params.R,
            )

            if dtau_E < dtau_E_min:
                involved_agents = (ball, cushion)
                dtau_E_min = dtau_E

    dtau_E = dtau_E_min

    return ball_linear_cushion_collision(*involved_agents, shot.t + dtau_E)


def get_next_ball_pocket_collision(
    shot: System, solver: QuarticSolver = QuarticSolver.HYBRID
) -> Event:
    """Returns next ball-pocket collision"""

    dtau_E = np.inf
    agent_ids = []
    collision_coeffs = []

    for ball in shot.balls.values():
        if ball.state.s in const.nontranslating:
            continue

        state = ball.state
        params = ball.params

        for pocket in shot.table.pockets.values():
            collision_coeffs.append(
                solve.ball_pocket_collision_coeffs(
                    rvw=state.rvw,
                    s=state.s,
                    a=pocket.a,
                    b=pocket.b,
                    r=pocket.radius,
                    mu=(params.u_s if state.s == const.sliding else params.u_r),
                    m=params.m,
                    g=params.g,
                    R=params.R,
                )
            )

            agent_ids.append((ball.id, pocket.id))

    if not len(collision_coeffs):
        # There are no collisions to test for
        return ball_pocket_collision(Ball.dummy(), Pocket.dummy(), shot.t + dtau_E)

    roots = solve_quartics(ps=np.array(collision_coeffs), solver=solver)
    dtau_E, index = roots.min(), roots.argmin()

    ball_id, pocket_id = agent_ids[index]
    ball, pocket = shot.balls[ball_id], shot.table.pockets[pocket_id]

    return ball_pocket_collision(ball, pocket, shot.t + dtau_E)
