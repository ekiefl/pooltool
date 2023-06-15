#! /usr/bin/env python

from __future__ import annotations

from itertools import combinations
from typing import Dict, Optional, Set

import attrs
import numpy as np

import pooltool.constants as const
import pooltool.math as math
import pooltool.physics as physics
from pooltool.events import (
    AgentType,
    Event,
    EventType,
    ball_ball_collision,
    ball_circular_cushion_collision,
    ball_linear_cushion_collision,
    ball_pocket_collision,
    null_event,
    rolling_spinning_transition,
    rolling_stationary_transition,
    sliding_rolling_transition,
    spinning_stationary_transition,
)
from pooltool.evolution.event_based import solve
from pooltool.evolution.event_based.config import INCLUDED_EVENTS
from pooltool.math.roots.quartic import QuarticSolver
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.table.components import (
    CircularCushionSegment,
    LinearCushionSegment,
    Pocket,
)
from pooltool.system.datatypes import System


def simulate(
    shot: System,
    include: Set[EventType] = INCLUDED_EVENTS,
    quartic_solver: QuarticSolver = QuarticSolver.HYBRID,
    t_final=None,
    continuize=False,
    dt=None,
) -> System:
    """Run a simulation on a system and return it"""

    shot.reset_history()
    shot.update_history(null_event(time=0))

    if dt is None:
        dt = 0.01

    transition_cache = TransitionCache.create(shot)

    while True:
        event = get_next_event(
            shot, transition_cache=transition_cache, quartic_solver=quartic_solver
        )

        if event.time == np.inf:
            shot.update_history(null_event(time=shot.t))
            break

        shot.evolve(event.time - shot.t)

        if event.event_type in include:
            shot.resolve_event(event)
            transition_cache.update(event)

        shot.update_history(event)

        if t_final is not None and shot.t >= t_final:
            shot.update_history(null_event(time=shot.t))
            break

    if continuize:
        shot.continuize(dt=dt)

    return shot


def get_next_event(
    shot: System,
    *,
    transition_cache: Optional[TransitionCache] = None,
    quartic_solver: QuarticSolver = QuarticSolver.HYBRID,
) -> Event:
    # Start by assuming next event doesn't happen
    event = null_event(time=np.inf)

    if transition_cache is None:
        transition_cache = TransitionCache.create(shot)

    transition_event = transition_cache.get_next()
    if transition_event.time < event.time:
        event = transition_event

    ball_ball_event = get_next_ball_ball_collision(shot, solver=quartic_solver)
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


@attrs.define
class TransitionCache:
    transitions: Dict[str, Event] = attrs.field()

    @transitions.default
    def _null(self):
        return {"null": null_event(time=np.inf)}

    def get_next(self) -> Event:
        return min(
            (trans for trans in self.transitions.values()), key=lambda event: event.time
        )

    def update(self, event: Event) -> None:
        """Update transition cache for all balls in Event"""
        for agent in event.agents:
            if agent.agent_type == AgentType.BALL:
                assert isinstance(ball := agent.final, Ball)
                self.transitions[agent.id] = _next_transition(ball)

    @classmethod
    def create(cls, shot: System) -> TransitionCache:
        return cls(
            {ball_id: _next_transition(ball) for ball_id, ball in shot.balls.items()}
        )


def _next_transition(ball: Ball) -> Event:
    if ball.state.s == const.stationary or ball.state.s == const.pocketed:
        return null_event(time=np.inf)

    elif ball.state.s == const.spinning:
        dtau_E = physics.get_spin_time(
            ball.state.rvw, ball.params.R, ball.params.u_sp, ball.params.g
        )
        return spinning_stationary_transition(ball, ball.state.t + dtau_E)

    elif ball.state.s == const.rolling:
        dtau_E_spin = physics.get_spin_time(
            ball.state.rvw, ball.params.R, ball.params.u_sp, ball.params.g
        )
        dtau_E_roll = physics.get_roll_time(
            ball.state.rvw, ball.params.u_r, ball.params.g
        )

        if dtau_E_spin > dtau_E_roll:
            return rolling_spinning_transition(ball, ball.state.t + dtau_E_roll)
        else:
            return rolling_stationary_transition(ball, ball.state.t + dtau_E_roll)

    elif ball.state.s == const.sliding:
        dtau_E = physics.get_slide_time(
            ball.state.rvw, ball.params.R, ball.params.u_s, ball.params.g
        )
        return sliding_rolling_transition(ball, ball.state.t + dtau_E)

    else:
        raise NotImplementedError(f"Unknown '{ball.state.s=}'")


def get_next_ball_ball_collision(
    shot: System, solver: QuarticSolver = QuarticSolver.HYBRID
) -> Event:
    """Returns next ball-ball collision"""

    dtau_E = np.inf
    ball_ids = []
    collision_coeffs = []

    for ball1, ball2 in combinations(shot.balls.values(), 2):
        ball1_state = ball1.state
        ball1_params = ball1.params

        ball2_state = ball2.state
        ball2_params = ball2.params

        if ball1_state.s == const.pocketed or ball2_state.s == const.pocketed:
            continue

        if (
            ball1_state.s in const.nontranslating
            and ball2_state.s in const.nontranslating
        ):
            continue

        if (
            math.norm3d(ball1_state.rvw[0] - ball2_state.rvw[0])
            < ball1_params.R + ball2_params.R
        ):
            # If balls are intersecting, avoid internal collisions
            continue

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

        ball_ids.append((ball1.id, ball2.id))

    if not len(collision_coeffs):
        # There are no collisions to test for
        return ball_ball_collision(Ball.dummy(), Ball.dummy(), shot.t + dtau_E)

    dtau_E, index = math.roots.quartic.minimum_quartic_root(
        ps=np.array(collision_coeffs), solver=solver
    )

    ball1_id, ball2_id = ball_ids[index]
    ball1, ball2 = shot.balls[ball1_id], shot.balls[ball2_id]

    return ball_ball_collision(ball1, ball2, shot.t + dtau_E)


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

    dtau_E, index = math.roots.quartic.minimum_quartic_root(
        ps=np.array(collision_coeffs), solver=solver
    )

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

    dtau_E, index = math.roots.quartic.minimum_quartic_root(
        ps=np.array(collision_coeffs), solver=solver
    )

    ball_id, pocket_id = agent_ids[index]
    ball, pocket = shot.balls[ball_id], shot.table.pockets[pocket_id]

    return ball_pocket_collision(ball, pocket, shot.t + dtau_E)
