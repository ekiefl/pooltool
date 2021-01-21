#! /usr/bin/env python

import psim
import psim.physics as physics

from abc import ABC, abstractmethod


class Event(ABC):
    event_class = None

    def __init__(self, *agents, t=None):
        self.time = t
        self.agents = agents

        if self.event_class is None:
            raise NotImplementedError("Child classes of Event must have a defined event_type")


    def __repr__(self):
        lines = [
            f'<{self.__class__.__module__}.{self.__class__.__name__} object at {hex(id(self))}>',
            f' ├── time   : {self.time}',
            f' └── agents : {[(agent.id if agent is not None else None) for agent in self.agents]}',
        ]

        return '\n'.join(lines) + '\n'


    def add_time(self, t):
        self.time += t


    @abstractmethod
    def resolve(self):
        pass


class Collision(Event):
    event_class = 'collision'

    def __init__(self, body1, body2, t=None):
        Event.__init__(self, body1, body2, t=t)


class BallBallCollision(Collision):
    event_type = 'ball-ball'

    def __init__(self, ball1, ball2, t=None):
        Collision.__init__(self, body1=ball1, body2=ball2, t=t)


    def resolve(self):
        ball1, ball2 = self.agents

        rvw1, rvw2 = physics.resolve_ball_ball_collision(ball1.rvw, ball2.rvw)
        s1, s2 = psim.sliding, psim.sliding

        ball1.set(rvw1, s1, t=self.time)
        ball1.update_next_transition_event()

        ball2.set(rvw2, s2, t=self.time)
        ball2.update_next_transition_event()


class BallCushionCollision(Collision):
    event_type = 'ball-cushion'

    def __init__(self, ball, cushion, t=None):
        Collision.__init__(self, body1=ball, body2=cushion, t=t)


    def resolve(self):
        ball, rail = self.agents

        rvw = physics.resolve_ball_rail_collision(
            rvw=ball.rvw,
            normal=rail.normal,
            R=ball.R,
            m=ball.m,
            h=rail.height,
        )
        s = psim.sliding

        ball.set(rvw, s, t=self.time)
        ball.update_next_transition_event()


class Transition(Event):
    event_class = 'transition'

    def __init__(self, ball, t=None):
        Event.__init__(self, ball, t=t)
        self.ball = self.agents[0]


    def resolve(self):
        self.ball.s = self.end_state
        self.ball.update_next_transition_event()


class SpinningStationaryTransition(Transition):
    event_type = 'spinning-stationary'

    def __init__(self, ball, t=None):
        Transition.__init__(self, ball, t=t)
        self.start_start, self.end_state = psim.spinning, psim.stationary


class RollingStationaryTransition(Transition):
    event_type = 'rolling-stationary'

    def __init__(self, ball, t=None):
        Transition.__init__(self, ball, t=t)
        self.start_start, self.end_state = psim.rolling, psim.stationary


class RollingSpinningTransition(Transition):
    event_class = 'rolling-spinning'

    def __init__(self, ball, t=None):
        Transition.__init__(self, ball, t=t)
        self.start_start, self.end_state = psim.rolling, psim.spinning


class SlidingRollingTransition(Transition):
    event_class = 'sliding-rolling'

    def __init__(self, ball, t=None):
        Transition.__init__(self, ball, t=t)
        self.start_start, self.end_state = psim.sliding, psim.rolling


class NonEvent(Event):
    event_class, event_type = 'none', 'none'

    def __init__(self, t=None):
        Event.__init__(self, t=t)


    def resolve(self):
        pass


class Events(object):
    def __init__(self, events=None):
        if events is not None:
            self.events = events
        else:
            self.events = []


    def add(self, event):
        self.events.append(event)


    def __repr__(self):
        return '\n\n'.join([event.__repr__() for event in self.events])
