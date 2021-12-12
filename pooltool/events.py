#! /usr/bin/env python

import pooltool.utils as utils
import pooltool.physics as physics
import pooltool.constants as c

from pooltool.error import ConfigError
from pooltool.objects import NonObject

import numpy as np
import collections.abc

from abc import ABC, abstractmethod

class_none = 'none'
class_collision = 'collision'
class_transition = 'transition'
type_none = 'none'
type_ball_ball = 'ball-ball'
type_ball_cushion = 'ball-cushion'
type_ball_pocket = 'ball-pocket'
type_stick_ball = 'stick-ball'
type_spinning_stationary = 'spinning-stationary'
type_rolling_stationary = 'rolling-stationary'
type_rolling_spinning = 'rolling-spinning'
type_sliding_rolling = 'sliding-rolling'


class Event(ABC):
    event_type, event_class = None, None

    def __init__(self, *agents, t=None):
        self.time = t
        self.agents = agents

        self.partial = True if not len(agents) else False

        if self.event_class is None:
            raise NotImplementedError("Child classes of Event must have a defined event_type")


    def __repr__(self):
        lines = [
            f'<{self.__class__.__name__} object at {hex(id(self))}>',
            f' ├── time   : {self.time}',
            f' └── agents : {[(agent.id if agent is not None else None) for agent in self.agents]}',
        ]

        return '\n'.join(lines) + '\n'


    def is_partial(self):
        if self.partial:
            raise ConfigError(f"Cannot call `{self.__class__.__name__}.resolve` when event is partial. Add agent objects.")


    @abstractmethod
    def resolve(self):
        pass


    @abstractmethod
    def as_dict(self):
        pass


    def save(self, path):
        utils.save_pickle(self.as_dict(), path)


class Collision(Event):
    event_class = class_collision

    def __init__(self, body1, body2, t=None):
        Event.__init__(self, body1, body2, t=t)

        self.agent1_state_initial = None
        self.agent2_state_initial = None
        self.agent1_state_final = None
        self.agent2_state_final = None


    def as_dict(self):
        return dict(
            event_class = self.event_class,
            event_type = self.event_type,
            agent_ids = [agent.id for agent in self.agents],
            agent1_state_initial = self.agent1_state_initial,
            agent2_state_initial = self.agent2_state_initial,
            agent1_state_final = self.agent1_state_final,
            agent2_state_final = self.agent2_state_final,
            t = self.time,
        )


class BallBallCollision(Collision):
    event_type = type_ball_ball

    def __init__(self, ball1, ball2, t=None):
        Collision.__init__(self, body1=ball1, body2=ball2, t=t)


    def resolve(self):
        self.is_partial()
        ball1, ball2 = self.agents

        self.agent1_state_initial = (np.copy(ball1.rvw), ball1.s)
        self.agent2_state_initial = (np.copy(ball2.rvw), ball2.s)

        rvw1, rvw2 = physics.resolve_ball_ball_collision(ball1.rvw, ball2.rvw)
        s1, s2 = c.sliding, c.sliding

        ball1.set(rvw1, s1, t=self.time)
        ball1.update_next_transition_event()

        ball2.set(rvw2, s2, t=self.time)
        ball2.update_next_transition_event()

        self.agent1_state_final = (np.copy(ball1.rvw), ball1.s)
        self.agent2_state_final = (np.copy(ball2.rvw), ball2.s)


class BallCushionCollision(Collision):
    event_type = type_ball_cushion

    def __init__(self, ball, cushion, t=None):
        Collision.__init__(self, body1=ball, body2=cushion, t=t)


    def resolve(self):
        self.is_partial()
        ball, cushion = self.agents
        normal = cushion.get_normal(ball.rvw)

        self.agent1_state_initial = (np.copy(ball.rvw), ball.s)

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

        self.agent1_state_final = (np.copy(ball.rvw), ball.s)


class StickBallCollision(Collision):
    event_type = type_stick_ball

    def __init__(self, cue_stick, ball, t=None):
        Collision.__init__(self, body1=cue_stick, body2=ball, t=t)


    def resolve(self):
        self.is_partial()
        cue_stick, ball = self.agents

        self.agent1_state_initial = (np.copy(ball.rvw), ball.s)

        v, w = physics.cue_strike(ball.m, cue_stick.M, ball.R, cue_stick.V0, cue_stick.phi, cue_stick.theta, cue_stick.a, cue_stick.b)
        rvw = np.array([ball.rvw[0], v, w])

        s = (c.rolling
             if abs(np.sum(utils.get_rel_velocity_fast(rvw, ball.R))) <= c.tol
             else c.sliding)

        ball.set(rvw, s)
        ball.update_next_transition_event()

        self.agent1_state_final = (np.copy(ball.rvw), ball.s)


class BallPocketCollision(Collision):
    event_type = type_ball_pocket

    def __init__(self, ball, pocket, t=None):
        Collision.__init__(self, body1=ball, body2=pocket, t=t)


    def resolve(self):
        self.is_partial()
        ball, pocket = self.agents

        self.agent1_state_initial = (np.copy(ball.rvw), ball.s)

        # Ball is placed at the pocket center
        rvw = np.array([[pocket.a, pocket.b, -pocket.depth],
                        [0,        0,         0           ],
                        [0,        0,         0           ]])

        ball.set(rvw, c.pocketed)
        ball.update_next_transition_event()

        pocket.add(ball.id)

        self.agent1_state_final = (np.copy(ball.rvw), ball.s)


class Transition(Event):
    event_class = class_transition

    def __init__(self, ball, t=None):
        Event.__init__(self, ball, t=t)

        self.agent_state_initial = None
        self.agent_state_final = None


    def resolve(self):
        ball = self.agents[0]

        self.is_partial()
        self.agent_state_initial = (np.copy(ball.rvw), self.state_start)

        ball.s = self.state_end
        ball.update_next_transition_event()

        self.agent_state_final = (np.copy(ball.rvw), self.state_end)


    def as_dict(self):
        return dict(
            event_class = self.event_class,
            event_type = self.event_type,
            agent_ids = [agent.id for agent in self.agents],
            agent_state_initial = self.agent_state_initial,
            agent_state_final = self.agent_state_final,
            t = self.time,
        )


class SpinningStationaryTransition(Transition):
    event_type = type_spinning_stationary

    def __init__(self, ball, t=None):
        Transition.__init__(self, ball, t=t)
        self.state_start, self.state_end = c.spinning, c.stationary


class RollingStationaryTransition(Transition):
    event_type = type_rolling_stationary

    def __init__(self, ball, t=None):
        Transition.__init__(self, ball, t=t)
        self.state_start, self.state_end = c.rolling, c.stationary


class RollingSpinningTransition(Transition):
    event_type = type_rolling_spinning

    def __init__(self, ball, t=None):
        Transition.__init__(self, ball, t=t)
        self.state_start, self.state_end = c.rolling, c.spinning


class SlidingRollingTransition(Transition):
    event_type = type_sliding_rolling

    def __init__(self, ball, t=None):
        Transition.__init__(self, ball, t=t)
        self.state_start, self.state_end = c.sliding, c.rolling


class NonEvent(Event):
    event_type = type_none
    event_class = class_none

    def __init__(self, t=None):
        Event.__init__(self, t=t)
        self.partial = False


    def resolve(self):
        self.is_partial()


    def as_dict(self):
        return dict(
            event_class = self.event_class,
            event_type = self.event_type,
            agent_ids = tuple(),
            t = self.time,
        )


class Events(collections.abc.MutableSequence):
    """Stores Event objects

    This is a list-like object. It supports len, del, insert, [], and append
    """

    def __init__(self):
        self._events = list()


    def __len__(self):
        return len(self._events)


    def __delitem__(self, index):
        self._events.__delitem__(index)


    def insert(self, index, value):
        self._events.insert(index, value)


    def __setitem__(self, index, value):
        self._events.__setitem__(index, value)


    def __getitem__(self, index):
        return self._events.__getitem__(index)


    def append(self, value):
        self.insert(len(self) + 1, value)


    def __repr__(self):
        return self._events.__repr__()


    def filter_type(self, types):
        """Return events in chronological order that are of an event type or types

        Parameters
        ==========
        types : str or list of str
            Event types to be filtered by. E.g. pooltool.events.type_ball_cushion or
            equivalently, 'ball-cushion'

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
        for event in self._events:
            if event.event_type in types:
                events.append(event)

        return events


    def filter_ball(self, balls, exclude=False):
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
        for event in self._events:
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

        idx = 0
        events = Events()
        for event in reversed(self._events):
            if event.time > t:
                events.append(event)
            else:
                break

        events._events = events._events[::-1]
        return events


    def reset(self):
        self._events = []


    def as_dict(self):
        return [event.as_dict() for event in self._events]


    def __repr__(self):
        return '\n'.join([f"{i}: {event.__repr__()}" for i, event in enumerate(self._events)])


def get_subclasses(cls):
    """Built upon https://stackoverflow.com/a/3862957"""
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in get_subclasses(c)]
    )
# event_classes looks like {
#    'spinning-stationary': <class 'pooltool.events.SpinningStationaryTransition'>,
#    'rolling-stationary': <class 'pooltool.events.RollingStationaryTransition'>,
#    'ball-ball': <class 'pooltool.events.BallBallCollision'>,
#    'ball-cushion': <class 'pooltool.events.BallCushionCollision'>,
#    (...)
# }
event_classes = {subcls.event_type: subcls for subcls in get_subclasses(Event)}


def event_from_dict(d):
    cls = event_classes[d['event_type']]

    # The constructed agents are placeholders
    agents = [NonObject(agent_id) for agent_id in d['agent_ids']]

    event = cls(*agents, t = d['t'])

    if d['event_class'] == class_collision:
        event.agent1_state_initial = d['agent1_state_initial']
        event.agent2_state_initial = d['agent2_state_initial']
        event.agent1_state_final = d['agent1_state_final']
        event.agent2_state_final = d['agent2_state_final']
    elif d['event_class'] == class_transition:
        event.agent_state_initial = d['agent_state_initial']
        event.agent_state_final = d['agent_state_final']

    # `partial` is set to True, which disables the ability to call event.resolve. This
    # is because NonObjects have been passed as the agents of this event
    event.partial = True

    return event







