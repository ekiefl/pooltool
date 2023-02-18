#! /usr/bin/env python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np

import pooltool.constants as c
import pooltool.physics as physics
import pooltool.utils as utils
from pooltool.objects import NullObject
from pooltool.objects.ball.datatypes import Ball, BallState
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
    BALL_CUSHION = strenum.auto()
    BALL_POCKET = strenum.auto()
    STICK_BALL = strenum.auto()
    SPINNING_STATIONARY = strenum.auto()
    ROLLING_STATIONARY = strenum.auto()
    ROLLING_SPINNING = strenum.auto()
    SLIDING_ROLLING = strenum.auto()

    def is_collision(self):
        return self in (
            EventType.BALL_BALL,
            EventType.BALL_CUSHION,
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

    def ball_transition_motion_states(self):
        """Return the ball motion states before and after a transition

        For example, if self == EventType.SPINNING_STATIONARY, return (c.spinning,
        c.stationary). Raises AssertionError if event is not a transition.
        """
        assert self.is_transition()

        if self == EventType.SPINNING_STATIONARY:
            return c.spinning, c.stationary
        elif self == EventType.ROLLING_STATIONARY:
            return c.rolling, c.stationary
        elif self == EventType.ROLLING_SPINNING:
            return c.rolling, c.spinning
        elif self == EventType.SLIDING_ROLLING:
            return c.sliding, c.rolling
        else:
            raise NotImplementedError()


def _get_state(agent) -> Optional[BallState]:
    if isinstance(agent, Ball):
        return agent.state.copy()
    return None


@dataclass
class Event:
    event_type: EventType
    agents: List[Any]
    time: float = 0

    initial_states: List[Optional[BallState]] = field(init=False)
    final_states: List[Optional[BallState]] = field(init=False, default_factory=list)

    def __post_init__(self):
        self.initial_states = [_get_state(agent) for agent in self.agents]

    def __repr__(self):
        agents = [(agent.id if agent is not None else None) for agent in self.agents]
        lines = [
            f"<{self.__class__.__name__} object at {hex(id(self))}>",
            f" ├── type   : {self.event_type}",
            f" ├── time   : {self.time}",
            f" └── agents : {agents}",
        ]

        return "\n".join(lines) + "\n"

    def assert_not_partial(self):
        """Raise AssertionError if agents are invalid

        In order to call resolve, there must exist at least one agent and it may not be
        a NullObject.
        """
        assert len(self.agents)
        for agent in self.agents:
            assert not isinstance(agent, NullObject)

    def resolve(self):
        event_resolvers[self.event_type](self)

    def save(self, path):
        raise NotImplementedError()


def null_event(time: float) -> Event:
    return Event(event_type=EventType.NONE, agents=[], time=time)


def ball_ball_collision(ball1: Ball, ball2: Ball, time: float) -> Event:
    return Event(event_type=EventType.BALL_BALL, agents=[ball1, ball2], time=time)


def ball_cushion_collision(
    ball: Ball,
    cushion: Union[LinearCushionSegment, CircularCushionSegment],
    time: float,
) -> Event:
    return Event(event_type=EventType.BALL_CUSHION, agents=[ball, cushion], time=time)


def ball_pocket_collision(ball: Ball, pocket: Pocket, time: float) -> Event:
    return Event(event_type=EventType.BALL_POCKET, agents=[ball, pocket], time=time)


def stick_ball_collision(stick: Cue, ball: Ball, time: float) -> Event:
    return Event(event_type=EventType.STICK_BALL, agents=[stick, ball], time=time)


def spinning_stationary_transition(ball: Ball, time: float) -> Event:
    return Event(event_type=EventType.SPINNING_STATIONARY, agents=[ball], time=time)


def rolling_stationary_transition(ball: Ball, time: float) -> Event:
    return Event(event_type=EventType.ROLLING_STATIONARY, agents=[ball], time=time)


def rolling_spinning_transition(ball: Ball, time: float) -> Event:
    return Event(event_type=EventType.ROLLING_SPINNING, agents=[ball], time=time)


def sliding_rolling_transition(ball: Ball, time: float) -> Event:
    return Event(event_type=EventType.SLIDING_ROLLING, agents=[ball], time=time)


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


def resolve_ball_ball(event):
    event.assert_not_partial()
    ball1, ball2 = event.agents

    rvw1, rvw2 = physics.resolve_ball_ball_collision(ball1.state.rvw, ball2.state.rvw)
    s1, s2 = c.sliding, c.sliding

    ball1.state.set(rvw1, s1, event.time)
    ball2.state.set(rvw2, s2, event.time)

    event.final_states = [ball1.state.copy(), ball2.state.copy()]


def resolve_null(event):
    event.assert_not_partial()


def resolve_ball_cushion(event):
    event.assert_not_partial()
    ball, cushion = event.agents
    normal = cushion.get_normal(ball.state.rvw)

    rvw = physics.resolve_ball_cushion_collision(
        rvw=ball.state.rvw,
        normal=normal,
        R=ball.params.R,
        m=ball.params.m,
        h=cushion.height,
        e_c=ball.params.e_c,
        f_c=ball.params.f_c,
    )
    s = c.sliding

    ball.state.set(rvw, s, t=event.time)

    event.final_states = [ball.state.copy(), None]


def resolve_ball_pocket(event):
    event.assert_not_partial()
    ball, pocket = event.agents

    # Ball is placed at the pocket center
    rvw = np.array([[pocket.a, pocket.b, -pocket.depth], [0, 0, 0], [0, 0, 0]])

    ball.state.set(rvw, c.pocketed)

    pocket.add(ball.id)

    event.final_states = [ball.state.copy(), None]


def resolve_stick_ball(event):
    event.assert_not_partial()
    cue_stick, ball = event.agents

    v, w = physics.cue_strike(
        ball.params.m,
        cue_stick.specs.M,
        ball.params.R,
        cue_stick.V0,
        cue_stick.phi,
        cue_stick.theta,
        cue_stick.a,
        cue_stick.b,
    )
    rvw = np.array([ball.state.rvw[0], v, w])

    s = (
        c.rolling
        if abs(np.sum(utils.get_rel_velocity_fast(rvw, ball.params.R))) <= c.tol
        else c.sliding
    )

    ball.state.set(rvw, s)

    event.final_states = [ball.state.copy(), None]


def resolve_transition(event):
    event.assert_not_partial()

    start, end = event.event_type.ball_transition_motion_states()

    ball = event.agents[0]
    ball.state.s = end

    event.final_states = [ball.state.copy()]


event_resolvers: Dict[EventType, Callable] = {
    EventType.NONE: resolve_null,
    EventType.BALL_BALL: resolve_ball_ball,
    EventType.BALL_CUSHION: resolve_ball_cushion,
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
        Event types to be filtered by. E.g. pooltool.events.EventType.BALL_CUSHION
        or equivalently, 'ball_cushion'

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
    events: List[Event], balls: Union[Ball, List[Ball]], keep_nonevent: bool = False
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

    if isinstance(balls, Ball):
        balls = [balls]

    new: List[Event] = []
    for event in events:
        if keep_nonevent and event.event_type == EventType.NONE:
            new.append(event)
        else:
            for ball in balls:
                if ball in event.agents:
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
