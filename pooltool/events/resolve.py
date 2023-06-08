from typing import Callable, Dict, Tuple

import numpy as np
from attrs import evolve

import pooltool.constants as c
import pooltool.physics as physics
from pooltool.events.datatypes import Event, EventType
from pooltool.objects.ball.datatypes import Ball, BallState
from pooltool.objects.cue.datatypes import Cue
from pooltool.objects.table.components import (
    CircularCushionSegment,
    LinearCushionSegment,
    Pocket,
)


def resolve_ball_ball(event: Event) -> Event:
    ball1, ball2 = event.agents

    assert isinstance(ball1.initial, Ball)
    assert isinstance(ball2.initial, Ball)

    rvw1, rvw2 = physics.resolve_ball_ball_collision(
        np.copy(ball1.initial.state.rvw),
        np.copy(ball2.initial.state.rvw),
        ball1.initial.params.R,
    )

    ball1.final = evolve(ball1.initial, state=BallState(rvw1, c.sliding, event.time))
    ball2.final = evolve(ball2.initial, state=BallState(rvw2, c.sliding, event.time))

    return event


def resolve_null(event: Event) -> Event:
    return event


def resolve_linear_ball_cushion(event: Event) -> Event:
    return _resolve_ball_cushion(event)


def resolve_circular_ball_cushion(event: Event) -> Event:
    return _resolve_ball_cushion(event)


def _resolve_ball_cushion(event: Event) -> Event:
    ball, cushion = event.agents

    assert isinstance(ball.initial, Ball)
    assert isinstance(cushion.initial, (LinearCushionSegment, CircularCushionSegment))

    rvw = ball.initial.state.rvw
    normal = cushion.initial.get_normal(rvw)

    rvw = physics.resolve_ball_cushion_collision(
        rvw=rvw,
        normal=normal,
        R=ball.initial.params.R,
        m=ball.initial.params.m,
        h=cushion.initial.height,
        e_c=ball.initial.params.e_c,
        f_c=ball.initial.params.f_c,
    )

    ball.final = evolve(ball.initial, state=BallState(rvw, c.sliding, event.time))
    cushion.final = None

    return event


def resolve_ball_pocket(event: Event) -> Event:
    ball, pocket = event.agents

    assert isinstance(ball.initial, Ball)
    assert isinstance(pocket.initial, Pocket)

    # Ball is placed at the pocket center
    rvw = np.array(
        [
            [pocket.initial.a, pocket.initial.b, -pocket.initial.depth],
            [0, 0, 0],
            [0, 0, 0],
        ]
    )

    ball.final = evolve(ball.initial, state=BallState(rvw, c.pocketed, event.time))
    pocket.final = pocket.initial.copy()
    pocket.final.add(ball.final.id)

    return event


def resolve_stick_ball(event: Event) -> Event:
    cue, ball = event.agents

    assert isinstance(ball.initial, Ball)
    assert isinstance(cue.initial, Cue)

    v, w = physics.cue_strike(
        ball.initial.params.m,
        cue.initial.specs.M,
        ball.initial.params.R,
        cue.initial.V0,
        cue.initial.phi,
        cue.initial.theta,
        cue.initial.a,
        cue.initial.b,
    )

    rvw = np.array([ball.initial.state.rvw[0], v, w])
    s = c.sliding

    ball.final = evolve(ball.initial, state=BallState(rvw, s, event.time))
    cue.final = None

    return event


def resolve_transition(event: Event) -> Event:
    ball = event.agents[0]

    assert isinstance(ball.initial, Ball)

    start, end = _ball_transition_motion_states(event.event_type)

    ball.final = ball.initial.copy()
    ball.final.state.s = end
    ball.initial.state.s = start

    return event


def _ball_transition_motion_states(event_type: EventType) -> Tuple[int, int]:
    """Return the ball motion states before and after a transition"""
    assert event_type.is_transition()

    if event_type == EventType.SPINNING_STATIONARY:
        return c.spinning, c.stationary
    elif event_type == EventType.ROLLING_STATIONARY:
        return c.rolling, c.stationary
    elif event_type == EventType.ROLLING_SPINNING:
        return c.rolling, c.spinning
    elif event_type == EventType.SLIDING_ROLLING:
        return c.sliding, c.rolling

    raise NotImplementedError()


event_resolvers: Dict[EventType, Callable] = {
    EventType.NONE: resolve_null,
    EventType.BALL_BALL: resolve_ball_ball,
    EventType.BALL_LINEAR_CUSHION: resolve_linear_ball_cushion,
    EventType.BALL_CIRCULAR_CUSHION: resolve_circular_ball_cushion,
    EventType.BALL_POCKET: resolve_ball_pocket,
    EventType.STICK_BALL: resolve_stick_ball,
    EventType.SPINNING_STATIONARY: resolve_transition,
    EventType.ROLLING_STATIONARY: resolve_transition,
    EventType.ROLLING_SPINNING: resolve_transition,
    EventType.SLIDING_ROLLING: resolve_transition,
}


def resolve_event(event: Event) -> Event:
    return event_resolvers[event.event_type](event)
