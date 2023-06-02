#! /usr/bin/env python

from __future__ import annotations

from typing import Set

import numpy as np

import pooltool.constants as c
import pooltool.math as math
import pooltool.physics as physics
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
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.table.components import (
    CircularCushionSegment,
    LinearCushionSegment,
    Pocket,
)
from pooltool.system.datatypes import System

DEFAULT_INCLUDE = {
    EventType.NONE,
    EventType.BALL_BALL,
    EventType.BALL_LINEAR_CUSHION,
    EventType.BALL_CIRCULAR_CUSHION,
    EventType.BALL_POCKET,
    EventType.STICK_BALL,
    EventType.SPINNING_STATIONARY,
    EventType.ROLLING_STATIONARY,
    EventType.ROLLING_SPINNING,
    EventType.SLIDING_ROLLING,
}


def simulate(
    shot: System,
    include: Set[EventType] = DEFAULT_INCLUDE,
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
            event = get_next_event(shot)

            if event.time == np.inf:
                shot.update_history(null_event(time=shot.t + c.tol))
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


def get_next_event(shot: System) -> Event:
    # Start by assuming next event doesn't happen
    event = null_event(time=np.inf)

    transition_event = get_next_transition(shot)
    if transition_event.time < event.time:
        event = transition_event

    ball_ball_event = get_next_ball_ball_collision(shot)
    if ball_ball_event.time < event.time:
        event = ball_ball_event

    ball_linear_cushion_event = get_next_ball_linear_cushion_collision(shot)
    if ball_linear_cushion_event.time < event.time:
        event = ball_linear_cushion_event

    ball_circular_cushion_event = get_next_ball_circular_cushion_event(shot)
    if ball_circular_cushion_event.time < event.time:
        event = ball_circular_cushion_event

    ball_pocket_event = get_next_ball_pocket_collision(shot)
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


def get_next_ball_ball_collision(shot: System) -> Event:
    """Returns next ball-ball collision"""

    dtau_E = np.inf
    ball_ids = []
    collision_coeffs = []

    for i, ball1 in enumerate(shot.balls.values()):
        for j, ball2 in enumerate(shot.balls.values()):
            if i >= j:
                continue

            if ball1.state.s == c.pocketed or ball2.state.s == c.pocketed:
                continue

            if ball1.state.s in c.nontranslating and ball2.state.s in c.nontranslating:
                continue

            collision_coeffs.append(
                physics.get_ball_ball_collision_coeffs_fast(
                    rvw1=ball1.state.rvw,
                    rvw2=ball2.state.rvw,
                    s1=ball1.state.s,
                    s2=ball2.state.s,
                    mu1=(
                        ball1.params.u_s
                        if ball1.state.s == c.sliding
                        else ball1.params.u_r
                    ),
                    mu2=(
                        ball2.params.u_s
                        if ball2.state.s == c.sliding
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

    dtau_E, index = math.min_real_root(p=np.array(collision_coeffs), tol=c.tol)

    ball1_id, ball2_id = ball_ids[index]
    ball1, ball2 = shot.balls[ball1_id], shot.balls[ball2_id]

    return ball_ball_collision(ball1, ball2, shot.t + dtau_E)


def get_next_ball_circular_cushion_event(shot: System) -> Event:
    """Returns next ball-cushion collision (circular cushion segment)"""

    dtau_E = np.inf
    agent_ids = []
    collision_coeffs = []

    for ball in shot.balls.values():
        if ball.state.s in c.nontranslating:
            continue

        for cushion in shot.table.cushion_segments.circular.values():
            collision_coeffs.append(
                physics.get_ball_circular_cushion_collision_coeffs_fast(
                    rvw=ball.state.rvw,
                    s=ball.state.s,
                    a=cushion.a,
                    b=cushion.b,
                    r=cushion.radius,
                    mu=(
                        ball.params.u_s
                        if ball.state.s == c.sliding
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

    dtau_E, index = math.min_real_root(p=np.array(collision_coeffs), tol=c.tol)

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
        if ball.state.s in c.nontranslating:
            continue

        for cushion in shot.table.cushion_segments.linear.values():
            dtau_E = physics.get_ball_linear_cushion_collision_time_fast(
                rvw=ball.state.rvw,
                s=ball.state.s,
                lx=cushion.lx,
                ly=cushion.ly,
                l0=cushion.l0,
                p1=cushion.p1,
                p2=cushion.p2,
                direction=cushion.direction.value,
                mu=(ball.params.u_s if ball.state.s == c.sliding else ball.params.u_r),
                m=ball.params.m,
                g=ball.params.g,
                R=ball.params.R,
            )

            if dtau_E < dtau_E_min:
                involved_agents = (ball, cushion)
                dtau_E_min = dtau_E

    dtau_E = dtau_E_min

    return ball_linear_cushion_collision(*involved_agents, shot.t + dtau_E)


def get_next_ball_pocket_collision(shot: System) -> Event:
    """Returns next ball-pocket collision"""

    dtau_E = np.inf
    agent_ids = []
    collision_coeffs = []

    for ball in shot.balls.values():
        if ball.state.s in c.nontranslating:
            continue

        for pocket in shot.table.pockets.values():
            collision_coeffs.append(
                physics.get_ball_pocket_collision_coeffs_fast(
                    rvw=ball.state.rvw,
                    s=ball.state.s,
                    a=pocket.a,
                    b=pocket.b,
                    r=pocket.radius,
                    mu=(
                        ball.params.u_s
                        if ball.state.s == c.sliding
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

    dtau_E, index = math.min_real_root(p=np.array(collision_coeffs), tol=c.tol)

    ball_id, pocket_id = agent_ids[index]
    ball, pocket = shot.balls[ball_id], shot.table.pockets[pocket_id]

    return ball_pocket_collision(ball, pocket, shot.t + dtau_E)
