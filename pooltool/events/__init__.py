#! /usr/bin/env python

from pooltool.events._events import Event, Events, EventType, event_resolvers
from pooltool.objects.ball import Ball
from pooltool.objects.cue import Cue
from pooltool.objects.table import CushionSegment, Pocket


def null_event(time: float) -> Event:
    return Event(event_type=EventType.NONE, agents=[], time=time)


def ball_ball_collision(ball1: Ball, ball2: Ball, time: float) -> Event:
    return Event(event_type=EventType.BALL_BALL, agents=[ball1, ball2], time=time)


def ball_cushion_collision(ball: Ball, cushion: CushionSegment, time: float) -> Event:
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
