#! /usr/bin/env python

from abc import ABC, abstractmethod
from typing import Dict

import numpy as np

import pooltool.constants as c
import pooltool.physics as physics
import pooltool.utils as utils
from pooltool.error import ConfigError
from pooltool.objects import NonObject
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


class Event(ABC):
    def __init__(self, *agents, t=None):
        self.time = t
        self.agents = agents
        self.initial_states: list
        self.final_states: list

        self.partial = not bool(len(agents))

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
        if self.partial:
            raise ConfigError(
                f"Cannot call `{self.__class__.__name__}.resolve` when event is "
                f"partial. Add agent objects."
            )

    @abstractmethod
    def resolve(self):
        pass

    def as_dict(self):
        return dict(
            event_type=self.event_type,
            agent_ids=list(),
            initial_states=self.initial_states,
            final_states=self.final_states,
            t=self.time,
        )

    def save(self, path):
        utils.save_pickle(self.as_dict(), path)


def _get_initial_states(agent):
    """This is a hack job FIXME

    Actual copies of the object should be made rather than storing just rvw and s
    """
    if hasattr(agent, "rvw"):
        return np.copy(agent.rvw), agent.s
    else:
        return None


class Collision(Event):
    def __init__(self, body1, body2, t=None):
        Event.__init__(self, body1, body2, t=t)
        self.initial_states = [_get_initial_states(agent) for agent in [body1, body2]]


class BallBallCollision(Collision):
    event_type = EventType.BALL_BALL

    def __init__(self, ball1, ball2, t=None):
        Collision.__init__(self, body1=ball1, body2=ball2, t=t)

    def resolve(self):
        self.assert_not_partial()
        ball1, ball2 = self.agents

        rvw1, rvw2 = physics.resolve_ball_ball_collision(ball1.rvw, ball2.rvw)
        s1, s2 = c.sliding, c.sliding

        ball1.set(rvw1, s1, t=self.time)
        ball1.update_next_transition_event()

        ball2.set(rvw2, s2, t=self.time)
        ball2.update_next_transition_event()

        self.final_states = [
            (np.copy(ball1.rvw), ball1.s),
            (np.copy(ball2.rvw), ball2.s),
        ]


class BallCushionCollision(Collision):
    event_type = EventType.BALL_CUSHION

    def __init__(self, ball, cushion, t=None):
        Collision.__init__(self, body1=ball, body2=cushion, t=t)

    def resolve(self):
        self.assert_not_partial()
        ball, cushion = self.agents
        normal = cushion.get_normal(ball.rvw)

        rvw = physics.resolve_ball_cushion_collision(
            rvw=ball.rvw,
            normal=normal,
            R=ball.R,
            m=ball.m,
            h=cushion.height,
            e_c=ball.e_c,
            f_c=ball.f_c,
        )
        s = c.sliding

        ball.set(rvw, s, t=self.time)
        ball.update_next_transition_event()

        self.final_states = [
            (np.copy(ball.rvw), ball.s),
            None,
        ]


class StickBallCollision(Collision):
    event_type = EventType.STICK_BALL

    def __init__(self, cue_stick, ball, t=None):
        Collision.__init__(self, body1=cue_stick, body2=ball, t=t)

    def resolve(self):
        self.assert_not_partial()
        cue_stick, ball = self.agents

        v, w = physics.cue_strike(
            ball.m,
            cue_stick.M,
            ball.R,
            cue_stick.V0,
            cue_stick.phi,
            cue_stick.theta,
            cue_stick.a,
            cue_stick.b,
        )
        rvw = np.array([ball.rvw[0], v, w])

        s = (
            c.rolling
            if abs(np.sum(utils.get_rel_velocity_fast(rvw, ball.R))) <= c.tol
            else c.sliding
        )

        ball.set(rvw, s)
        ball.update_next_transition_event()

        self.final_states = [
            (np.copy(ball.rvw), ball.s),
            None,
        ]


class BallPocketCollision(Collision):
    event_type = EventType.BALL_POCKET

    def __init__(self, ball, pocket, t=None):
        Collision.__init__(self, body1=ball, body2=pocket, t=t)

    def resolve(self):
        self.assert_not_partial()
        ball, pocket = self.agents

        # Ball is placed at the pocket center
        rvw = np.array([[pocket.a, pocket.b, -pocket.depth], [0, 0, 0], [0, 0, 0]])

        ball.set(rvw, c.pocketed)
        ball.update_next_transition_event()

        pocket.add(ball.id)

        self.final_states = [
            (np.copy(ball.rvw), ball.s),
            None,
        ]


class Transition(Event):
    def __init__(self, event_type: EventType, ball, t=None):
        Event.__init__(self, ball, t=t)
        self.event_type = event_type
        self.initial_states = _get_initial_states(ball)

    def resolve(self):
        self.assert_not_partial()

        ball = self.agents[0]

        start, end = self.event_type.ball_transition_motion_states()

        self.agent_state_initial = (np.copy(ball.rvw), start)

        ball.s = end
        ball.update_next_transition_event()

        self.final_states = [(np.copy(ball.rvw), end)]


class NonEvent(Event):
    event_type = EventType.NONE

    def __init__(self, t=None):
        Event.__init__(self, t=t)
        self.initial_states = []
        self.final_states = []
        self.partial = False

    def resolve(self):
        self.assert_not_partial()


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


event_dict: Dict[EventType, Event] = {
    EventType.NONE: NonEvent,
    EventType.BALL_BALL: BallBallCollision,
    EventType.BALL_CUSHION: BallCushionCollision,
    EventType.BALL_POCKET: BallPocketCollision,
    EventType.STICK_BALL: StickBallCollision,
    EventType.SPINNING_STATIONARY: Transition,
    EventType.ROLLING_STATIONARY: Transition,
    EventType.ROLLING_SPINNING: Transition,
    EventType.SLIDING_ROLLING: Transition,
}


def event_from_dict(d):
    cls = event_dict[d["event_type"]]

    # The constructed agents are placeholders
    agents = [NonObject(agent_id) for agent_id in d["agent_ids"]]

    # FIXME
    if d["event_type"].is_transition():
        event = cls(event_type=d["event_type"], ball=agents[0], t=d["t"])
    else:
        event = cls(*agents, t=d["t"])

    event.initial_states = d["initial_states"]
    event.final_states = d["final_states"]

    # `partial` is set to True, which disables the ability to call event.resolve. This
    # is because NonObjects have been passed as the agents of this event
    event.partial = True

    return event
