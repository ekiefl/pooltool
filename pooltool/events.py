#! /usr/bin/env python

import pooltool
import pooltool.utils as utils
import pooltool.physics as physics

import numpy as np

from abc import ABC, abstractmethod

class_none = 'none'
class_collision = 'collision'
class_transition = 'transition'
type_none = 'none'
type_ball_ball = 'ball-ball'
type_ball_cushion = 'ball-cushion'
type_stick_ball = 'stick-ball'
type_spinning_stationary = 'spinning-stationary'
type_rolling_stationary = 'rolling-stationary'
type_rolling_spinning = 'rolling-spinning'
type_sliding_rolling = 'sliding-rolling'


class Event(ABC):
    event_class = class_none

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
    event_class = class_collision

    def __init__(self, body1, body2, t=None):
        Event.__init__(self, body1, body2, t=t)


class BallBallCollision(Collision):
    event_type = type_ball_ball

    def __init__(self, ball1, ball2, t=None):
        self.ball1_state_start = ball1.s
        self.ball1_state_end = pooltool.sliding

        self.ball2_state_start = ball2.s
        self.ball2_state_end = pooltool.sliding

        Collision.__init__(self, body1=ball1, body2=ball2, t=t)


    def resolve(self):
        ball1, ball2 = self.agents

        rvw1, rvw2 = physics.resolve_ball_ball_collision(ball1.rvw, ball2.rvw)
        s1, s2 = pooltool.sliding, pooltool.sliding

        ball1.set(rvw1, s1, t=self.time)
        ball1.update_next_transition_event()

        ball2.set(rvw2, s2, t=self.time)
        ball2.update_next_transition_event()

        # We find the minimum required representation of the angular velocity integration vector.
        # Comment this out and see what happens if you don't do this. FIXME the solutioin is to get
        # rid of angular velocity integration vector and calculate the quaternions directly from
        # angular velocity
        ball1.rvw[3] = utils.normalize_rotation_vector(ball1.rvw[3])
        ball2.rvw[3] = utils.normalize_rotation_vector(ball2.rvw[3])


class BallCushionCollision(Collision):
    event_type = type_ball_cushion

    def __init__(self, ball, cushion, t=None):
        self.state_start = ball.s
        self.state_end = pooltool.sliding

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
        s = pooltool.sliding

        ball.set(rvw, s, t=self.time)
        ball.update_next_transition_event()

        # We find the minimum required representation of the angular velocity integration vector.
        # Comment this out and see what happens if you don't do this. FIXME the solutioin is to get
        # rid of angular velocity integration vector and calculate the quaternions directly from
        # angular velocity
        ball.rvw[3] = utils.normalize_rotation_vector(ball.rvw[3])


class StickBallCollision(Collision):
    event_type = type_stick_ball

    def __init__(self, cue_stick, ball, t=None):
        self.state_start = ball.s
        self.state_end = pooltool.sliding

        Collision.__init__(self, body1=cue_stick, body2=ball, t=t)


    def resolve(self):
        cue_stick, ball = self.agents

        v, w = physics.cue_strike(ball.m, cue_stick.M, ball.R, cue_stick.V0, cue_stick.phi, cue_stick.theta, cue_stick.a, cue_stick.b)
        rvw = np.array([ball.rvw[0], v, w, ball.rvw[3]])

        s = (pooltool.rolling
             if abs(np.sum(physics.get_rel_velocity(rvw, ball.R))) <= pooltool.tol
             else pooltool.sliding)

        ball.set(rvw, s)
        ball.update_next_transition_event()


class Transition(Event):
    event_class = class_transition

    def __init__(self, ball, t=None):
        Event.__init__(self, ball, t=t)
        self.ball = self.agents[0]


    def resolve(self):
        self.ball.s = self.state_end
        self.ball.update_next_transition_event()

        # We find the minimum required representation of the angular velocity integration vector.
        # Comment this out and see what happens if you don't do this. FIXME the solutioin is to get
        # rid of angular velocity integration vector and calculate the quaternions directly from
        # angular velocity
        self.ball.rvw[3] = utils.normalize_rotation_vector(self.ball.rvw[3])


class SpinningStationaryTransition(Transition):
    event_type = type_spinning_stationary

    def __init__(self, ball, t=None):
        Transition.__init__(self, ball, t=t)
        self.state_start, self.state_end = pooltool.spinning, pooltool.stationary


class RollingStationaryTransition(Transition):
    event_type = type_rolling_stationary

    def __init__(self, ball, t=None):
        Transition.__init__(self, ball, t=t)
        self.state_start, self.state_end = pooltool.rolling, pooltool.stationary


class RollingSpinningTransition(Transition):
    event_type = type_rolling_spinning

    def __init__(self, ball, t=None):
        Transition.__init__(self, ball, t=t)
        self.state_start, self.state_end = pooltool.rolling, pooltool.spinning


class SlidingRollingTransition(Transition):
    event_type = type_sliding_rolling

    def __init__(self, ball, t=None):
        Transition.__init__(self, ball, t=t)
        self.state_start, self.state_end = pooltool.sliding, pooltool.rolling


class NonEvent(Event):
    event_class, event_type = class_none, type_none

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

        self.num_events = 0


    def add_event(self, event):
        self.events.append(event)
        self.num_events += 1


    def reset_events(self):
        self.events = []
        self.num_events = 0


    def __repr__(self):
        return '\n'.join([event.__repr__() for event in self.events])























