from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

import numpy as np

import pooltool.constants as c
import pooltool.utils as utils
from pooltool.events.resolve import (
    resolve_ball_ball,
    resolve_ball_cushion,
    resolve_ball_pocket,
    resolve_null,
    resolve_stick_ball,
    resolve_transition,
)
from pooltool.objects import NonObject, Object
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


def _get_initial_states(agent):
    """This is a hack job FIXME

    Actual copies of the object should be made rather than storing just rvw and s
    """
    if hasattr(agent, "rvw"):
        return np.copy(agent.rvw), agent.s
    else:
        return None


@dataclass
class Event:
    event_type: EventType
    agents: List[Object]
    time: float = 0

    initial_states: Any = field(init=False)
    final_states: Any = field(init=False, default=None)

    def __post_init__(self):
        self.initial_states = [_get_initial_states(agent) for agent in self.agents]

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
        a NonObject.
        """
        assert len(self.agents)
        for agent in self.agents:
            assert not isinstance(agent, NonObject)

    def resolve(self):
        event_resolvers[self.event_type](self)

    def as_dict(self):
        return dict(
            event_type=self.event_type,
            agent_ids=[agent.id for agent in self.agents],
            initial_states=self.initial_states,
            final_states=self.final_states,
            time=self.time,
        )

    def save(self, path):
        utils.save_pickle(self.as_dict(), path)

    @classmethod
    def from_dict(cls, d) -> Event:
        # The constructed agents are placeholders
        agents = [NonObject(agent_id) for agent_id in d["agent_ids"]]

        event = Event(event_type=d["event_type"], agents=agents, time=d["time"])

        event.initial_states = d["initial_states"]
        event.final_states = d["final_states"]

        return event


@dataclass
class NonEvent(Event):
    event_type: EventType = field(init=False, default=EventType.NONE)
    agents: List[Object] = field(init=False, default_factory=list)


class Events(utils.ListLike):
    """Stores Event objects"""

    def filter_type(self, types):
        """Return events in chronological order that are of an event type or types

        Parameters
        ==========
        types : str or list of str
            Event types to be filtered by. E.g. pooltool.events.EventType.BALL_CUSHION
            or equivalently, 'ball_cushion'

        Returns
        =======
        events : pooltool.events.Events
            A subset Events object containing events only of specified types
        """

        try:
            iter(types)
        except TypeError:
            types = [types]

        events = Events()
        for event in self._list:
            if event.event_type in types:
                events.append(event)

        return events

    def filter_ball(self, balls, keep_nonevent=False):
        """Return events in chronological order that involve a collection of balls

        Parameters
        ==========
        balls : pooltool.objects.ball.Ball or list of pooltool.objects.ball.Ball
            Balls that you want events for.

        Returns
        =======
        events : pooltool.events.Events
            A subset Events object containing events only with specified balls
        """

        try:
            iter(balls)
        except TypeError:
            balls = [balls]

        events = Events()
        for event in self._list:
            if keep_nonevent and event.event_type == EventType.NONE:
                events.append(event)
            else:
                for ball in balls:
                    if ball in event.agents:
                        events.append(event)
                        break

        return events

    def filter_time(self, t):
        """Return events in chronological order after a certain time

        Parameters
        ==========
        t : float
            time after which you want events for

        Returns
        =======
        events : pooltool.events.Events
            A subset Events object containing events only after specified time
        """

        events = Events()
        for event in reversed(self._list):
            if event.time > t:
                events.append(event)
            else:
                break

        events._list = events._list[::-1]
        return events

    def reset(self):
        self._list = []

    def as_dict(self):
        return [event.as_dict() for event in self._list]

    def __repr__(self):
        return "\n".join(
            [f"{i}: {event.__repr__()}" for i, event in enumerate(self._list)]
        )
