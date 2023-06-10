#! /usr/bin/env python

from __future__ import annotations

from itertools import combinations
from typing import Set

import numpy as np

import pooltool.constants as const
import pooltool.math as math
from pooltool.error import SimulateError
from pooltool.events import (
    Event,
    EventType,
    ball_ball_collision,
    ball_circular_cushion_collision,
    ball_linear_cushion_collision,
    ball_pocket_collision,
    get_next_transition_event,
    null_event,
)
from pooltool.evolution.event_based import solve
from pooltool.evolution.event_based.config import INCLUDED_EVENTS
from pooltool.math.roots import QuarticSolver
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
    quartic_solver: QuarticSolver = QuarticSolver.OLD,
    raise_simulate_error: bool = False,
    t_final=None,
    continuize=False,
    dt=None,
) -> System:
    """Run a simulation on a system and return it"""

    shot.reset_history()
    shot.update_history(null_event(time=0))

    try:
        if dt is None:
            dt = 0.01

        while True:
            event = get_next_event(shot, quartic_solver=quartic_solver)

            if event.time == np.inf:
                shot.update_history(null_event(time=shot.t))
                break

            shot.evolve(event.time - shot.t)

            if event.event_type in include:
                shot.resolve_event(event)

            shot.update_history(event)

            if t_final is not None and shot.t >= t_final:
                break

        if continuize:
            shot.continuize(dt=dt)

    except Exception as exc:
        if raise_simulate_error:
            raise SimulateError()
        else:
            raise exc

    return shot


def get_next_event(
    shot: System, quartic_solver: QuarticSolver = QuarticSolver.OLD
) -> Event:
    # Start by assuming next event doesn't happen
    event = null_event(time=np.inf)

    transition_event = get_next_transition(shot)
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


def get_next_transition(shot: System) -> Event:
    """Returns next ball transition event"""

    event = null_event(time=np.inf)

    for ball in shot.balls.values():
        trans_event = get_next_transition_event(ball)
        if trans_event.time <= event.time:
            event = trans_event

    return event


def get_next_ball_ball_collision(
    shot: System, solver: QuarticSolver = QuarticSolver.OLD
) -> Event:
    """Returns next ball-ball collision"""

    dtau_E = np.inf
    ball_ids = []
    collision_coeffs = []

    for ball1, ball2 in combinations(shot.balls.values(), 2):
        if ball1.state.s == const.pocketed or ball2.state.s == const.pocketed:
            continue

        if (
            ball1.state.s in const.nontranslating
            and ball2.state.s in const.nontranslating
        ):
            continue

        collision_coeffs.append(
            solve.ball_ball_collision_coeffs(
                rvw1=ball1.state.rvw,
                rvw2=ball2.state.rvw,
                s1=ball1.state.s,
                s2=ball2.state.s,
                mu1=(
                    ball1.params.u_s
                    if ball1.state.s == const.sliding
                    else ball1.params.u_r
                ),
                mu2=(
                    ball2.params.u_s
                    if ball2.state.s == const.sliding
                    else ball2.params.u_r
                ),
                m1=ball1.params.m,
                m2=ball2.params.m,
                g1=ball1.params.g,
                g2=ball2.params.g,
                R=ball1.params.R,
            )
        )

        ball_ids.append((ball1.id, ball2.id))

    if not len(collision_coeffs):
        # There are no collisions to test for
        return ball_ball_collision(Ball.dummy(), Ball.dummy(), shot.t + dtau_E)

    dtau_E, index = math.min_real_root(p=np.array(collision_coeffs), solver=solver)

    ball1_id, ball2_id = ball_ids[index]
    ball1, ball2 = shot.balls[ball1_id], shot.balls[ball2_id]

    return ball_ball_collision(ball1, ball2, shot.t + dtau_E)


def get_next_ball_circular_cushion_event(
    shot: System, solver: QuarticSolver = QuarticSolver.OLD
) -> Event:
    """Returns next ball-cushion collision (circular cushion segment)"""

    dtau_E = np.inf
    agent_ids = []
    collision_coeffs = []

    for ball in shot.balls.values():
        if ball.state.s in const.nontranslating:
            continue

        for cushion in shot.table.cushion_segments.circular.values():
            collision_coeffs.append(
                solve.ball_circular_cushion_collision_coeffs(
                    rvw=ball.state.rvw,
                    s=ball.state.s,
                    a=cushion.a,
                    b=cushion.b,
                    r=cushion.radius,
                    mu=(
                        ball.params.u_s
                        if ball.state.s == const.sliding
                        else ball.params.u_r
                    ),
                    m=ball.params.m,
                    g=ball.params.g,
                    R=ball.params.R,
                )
            )

            agent_ids.append((ball.id, cushion.id))

    if not len(collision_coeffs):
        # There are no collisions to test for
        return ball_circular_cushion_collision(
            Ball.dummy(), CircularCushionSegment.dummy(), shot.t + dtau_E
        )

    dtau_E, index = math.min_real_root(p=np.array(collision_coeffs), solver=solver)

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

        for cushion in shot.table.cushion_segments.linear.values():
            dtau_E = solve.ball_linear_cushion_collision_time(
                rvw=ball.state.rvw,
                s=ball.state.s,
                lx=cushion.lx,
                ly=cushion.ly,
                l0=cushion.l0,
                p1=cushion.p1,
                p2=cushion.p2,
                direction=cushion.direction.value,
                mu=(
                    ball.params.u_s
                    if ball.state.s == const.sliding
                    else ball.params.u_r
                ),
                m=ball.params.m,
                g=ball.params.g,
                R=ball.params.R,
            )

            if dtau_E < dtau_E_min:
                involved_agents = (ball, cushion)
                dtau_E_min = dtau_E

    dtau_E = dtau_E_min

    return ball_linear_cushion_collision(*involved_agents, shot.t + dtau_E)


def get_next_ball_pocket_collision(
    shot: System, solver: QuarticSolver = QuarticSolver.OLD
) -> Event:
    """Returns next ball-pocket collision"""

    dtau_E = np.inf
    agent_ids = []
    collision_coeffs = []

    for ball in shot.balls.values():
        if ball.state.s in const.nontranslating:
            continue

        for pocket in shot.table.pockets.values():
            collision_coeffs.append(
                solve.ball_pocket_collision_coeffs(
                    rvw=ball.state.rvw,
                    s=ball.state.s,
                    a=pocket.a,
                    b=pocket.b,
                    r=pocket.radius,
                    mu=(
                        ball.params.u_s
                        if ball.state.s == const.sliding
                        else ball.params.u_r
                    ),
                    m=ball.params.m,
                    g=ball.params.g,
                    R=ball.params.R,
                )
            )

            agent_ids.append((ball.id, pocket.id))

    if not len(collision_coeffs):
        # There are no collisions to test for
        return ball_pocket_collision(Ball.dummy(), Pocket.dummy(), shot.t + dtau_E)

    dtau_E, index = math.min_real_root(p=np.array(collision_coeffs), solver=solver)

    ball_id, pocket_id = agent_ids[index]
    ball, pocket = shot.balls[ball_id], shot.table.pockets[pocket_id]

    return ball_pocket_collision(ball, pocket, shot.t + dtau_E)
