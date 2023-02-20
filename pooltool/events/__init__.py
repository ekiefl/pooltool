#! /usr/bin/env python
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable, Dict, List, Optional, Tuple, Union

import numpy as np

import pooltool.constants as c
import pooltool.physics as physics
import pooltool.utils as utils
from pooltool.objects.ball.datatypes import Ball, BallHistory, BallState
from pooltool.objects.cue.datatypes import Cue
from pooltool.objects.table.components import (
    CircularCushionSegment,
    LinearCushionSegment,
    Pocket,
)
from pooltool.utils import strenum


class EventType(strenum.StrEnum):
    NONE = strenum.auto()
    BALL_BALL = strenum.auto()
    BALL_LINEAR_CUSHION = strenum.auto()
    BALL_CIRCULAR_CUSHION = strenum.auto()
    BALL_POCKET = strenum.auto()
    STICK_BALL = strenum.auto()
    SPINNING_STATIONARY = strenum.auto()
    ROLLING_STATIONARY = strenum.auto()
    ROLLING_SPINNING = strenum.auto()
    SLIDING_ROLLING = strenum.auto()

    def is_collision(self):
        return self in (
            EventType.BALL_BALL,
            EventType.BALL_CIRCULAR_CUSHION,
            EventType.BALL_LINEAR_CUSHION,
            EventType.BALL_POCKET,
            EventType.STICK_BALL,
        )

    def is_transition(self):
        return self in (
            EventType.SPINNING_STATIONARY,
            EventType.ROLLING_STATIONARY,
            EventType.ROLLING_SPINNING,
            EventType.SLIDING_ROLLING,
        )


Snapshot = Optional[
    Union[
        Ball,
        Cue,
        CircularCushionSegment,
        LinearCushionSegment,
        Pocket,
    ]
]


@dataclass
class Agent:
    initial: Snapshot
    final: Optional[Snapshot] = field(default=None)

    @staticmethod
    def null() -> Agent:
        return Agent(initial=None)

    @staticmethod
    def from_cue(cue: Cue) -> Agent:
        return Agent(initial=cue.copy())

    @staticmethod
    def from_ball(ball: Ball) -> Agent:
        snapshot = ball.copy()
        snapshot.history = BallHistory()
        snapshot.history_cts = BallHistory()

        return Agent(initial=snapshot)

    @staticmethod
    def from_pocket(pocket: Pocket) -> Agent:
        return Agent(initial=pocket.copy())

    @staticmethod
    def from_linear_cushion(linear_seg: LinearCushionSegment) -> Agent:
        return Agent(initial=linear_seg.copy())

    @staticmethod
    def from_circular_cushion(circ_seg: CircularCushionSegment) -> Agent:
        return Agent(initial=circ_seg.copy())


@dataclass
class Event:
    event_type: EventType
    agents: Tuple[Agent, ...]
    time: float

    def __repr__(self):
        agents = [
            (agent.initial.id if agent.initial is not None else None)
            for agent in self.agents
        ]
        lines = [
            f"<{self.__class__.__name__} object at {hex(id(self))}>",
            f" ├── type   : {self.event_type}",
            f" ├── time   : {self.time}",
            f" └── agents : {agents}",
        ]
        return "\n".join(lines) + "\n"

    def resolve(self):
        event_resolvers[self.event_type](self)


def null_event(time: float) -> Event:
    return Event(
        event_type=EventType.NONE,
        agents=(Agent.null(),),
        time=time,
    )


def ball_ball_collision(ball1: Ball, ball2: Ball, time: float) -> Event:
    return Event(
        event_type=EventType.BALL_BALL,
        agents=(
            Agent.from_ball(ball1),
            Agent.from_ball(ball2),
        ),
        time=time,
    )


def ball_linear_cushion_collision(
    ball: Ball, cushion: LinearCushionSegment, time: float
) -> Event:
    return Event(
        event_type=EventType.BALL_LINEAR_CUSHION,
        agents=(Agent.from_ball(ball), Agent.from_linear_cushion(cushion)),
        time=time,
    )


def ball_circular_cushion_collision(
    ball: Ball, cushion: CircularCushionSegment, time: float
) -> Event:
    return Event(
        event_type=EventType.BALL_CIRCULAR_CUSHION,
        agents=(Agent.from_ball(ball), Agent.from_circular_cushion(cushion)),
        time=time,
    )


def ball_pocket_collision(ball: Ball, pocket: Pocket, time: float) -> Event:
    return Event(
        event_type=EventType.BALL_POCKET,
        agents=(
            Agent.from_ball(ball),
            Agent.from_pocket(pocket),
        ),
        time=time,
    )


def stick_ball_collision(stick: Cue, ball: Ball, time: float) -> Event:
    return Event(
        event_type=EventType.STICK_BALL,
        agents=(
            Agent.from_cue(stick),
            Agent.from_ball(ball),
        ),
        time=time,
    )


def spinning_stationary_transition(ball: Ball, time: float) -> Event:
    return Event(
        event_type=EventType.SPINNING_STATIONARY,
        agents=(Agent.from_ball(ball),),
        time=time,
    )


def rolling_stationary_transition(ball: Ball, time: float) -> Event:
    return Event(
        event_type=EventType.ROLLING_STATIONARY,
        agents=(Agent.from_ball(ball),),
        time=time,
    )


def rolling_spinning_transition(ball: Ball, time: float) -> Event:
    return Event(
        event_type=EventType.ROLLING_SPINNING,
        agents=(Agent.from_ball(ball),),
        time=time,
    )


def sliding_rolling_transition(ball: Ball, time: float) -> Event:
    return Event(
        event_type=EventType.SLIDING_ROLLING,
        agents=(Agent.from_ball(ball),),
        time=time,
    )


def get_next_transition_event(ball: Ball) -> Event:
    if ball.state.s == c.stationary or ball.state.s == c.pocketed:
        return null_event(time=np.inf)

    elif ball.state.s == c.spinning:
        dtau_E = physics.get_spin_time_fast(
            ball.state.rvw, ball.params.R, ball.params.u_sp, ball.params.g
        )
        return spinning_stationary_transition(ball, ball.state.t + dtau_E)

    elif ball.state.s == c.rolling:
        dtau_E_spin = physics.get_spin_time_fast(
            ball.state.rvw, ball.params.R, ball.params.u_sp, ball.params.g
        )
        dtau_E_roll = physics.get_roll_time_fast(
            ball.state.rvw, ball.params.u_r, ball.params.g
        )

        if dtau_E_spin > dtau_E_roll:
            return rolling_spinning_transition(ball, ball.state.t + dtau_E_roll)
        else:
            return rolling_stationary_transition(ball, ball.state.t + dtau_E_roll)

    elif ball.state.s == c.sliding:
        dtau_E = physics.get_slide_time_fast(
            ball.state.rvw, ball.params.R, ball.params.u_s, ball.params.g
        )
        return sliding_rolling_transition(ball, ball.state.t + dtau_E)

    else:
        raise NotImplementedError(f"Unknown '{ball.state.s=}'")


def resolve_ball_ball(event: Event):
    ball1, ball2 = event.agents

    assert isinstance(ball1.initial, Ball)
    assert isinstance(ball2.initial, Ball)

    rvw1, rvw2 = physics.resolve_ball_ball_collision(
        ball1.initial.state.rvw, ball2.initial.state.rvw
    )

    ball1.final = replace(ball1.initial, state=BallState(rvw1, c.sliding, event.time))
    ball2.final = replace(ball2.initial, state=BallState(rvw2, c.sliding, event.time))


def resolve_null(event: Event):
    pass


def resolve_linear_ball_cushion(event: Event):
    _resolve_ball_cushion(event)


def resolve_circular_ball_cushion(event: Event):
    _resolve_ball_cushion(event)


def _resolve_ball_cushion(event: Event):
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

    ball.final = replace(ball.initial, state=BallState(rvw, c.sliding, event.time))
    cushion.final = None


def resolve_ball_pocket(event: Event):
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

    ball.final = replace(ball.initial, state=BallState(rvw, c.pocketed, event.time))
    pocket.final = pocket.initial.copy()
    pocket.final.add(ball.final.id)


def resolve_stick_ball(event: Event):
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
    s = (
        c.rolling
        if abs(np.sum(utils.get_rel_velocity_fast(rvw, ball.initial.params.R))) <= c.tol
        else c.sliding
    )

    ball.final = replace(ball.initial, state=BallState(rvw, s, event.time))
    cue.final = None


def resolve_transition(event: Event):
    ball = event.agents[0]

    assert isinstance(ball.initial, Ball)

    start, end = _ball_transition_motion_states(event.event_type)

    ball.final = ball.initial.copy()
    ball.final.state.s = end


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


def filter_type(
    events: List[Event], types: Union[EventType, List[EventType]]
) -> List[Event]:
    """Return events in chronological order that are of an event type or types

    Parameters
    ==========
    types : str or list of str
        Event types to be filtered by. E.g.
        pooltool.events.EventType.BALL_CIRCULAR_CUSHION or equivalently,
        'ball_circular_cushion'

    Returns
    =======
    events:
        A subset of events that are of the specified types.
    """

    if isinstance(types, str):
        types = [types]

    new: List[Event] = []
    for event in events:
        if event.event_type in types:
            new.append(event)

    return new


def filter_ball(
    events: List[Event], balls: Union[str, List[str]], keep_nonevent: bool = False
) -> List[Event]:
    """Return events in chronological order that involve a collection of balls

    Parameters
    ==========
    balls : pooltool.objects.ball.Ball or list of pooltool.objects.ball.Ball
        Balls that you want events for.

    Returns
    =======
    events:
        A subset of events involving specified balls.
    """

    if isinstance(balls, str):
        balls = [balls]

    new: List[Event] = []
    for event in events:
        if keep_nonevent and event.event_type == EventType.NONE:
            new.append(event)
        else:
            for agent in event.agents:
                if isinstance(agent.initial, Ball) and agent.initial.id in balls:
                    new.append(event)
                    break

    return new


def filter_time(events: List[Event], t: float) -> List[Event]:
    """Return events in chronological order after a certain time

    Parameters
    ==========
    t : float
        time after which you want events for

    Returns
    =======
    events:
        A subset of events occurring after specified time, non-inclusive.
    """

    new: List[Event] = []
    for event in reversed(events):
        if event.time > t:
            new.append(event)
        else:
            break

    return new[::-1]
