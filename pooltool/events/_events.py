from __future__ import annotations

import numpy as np

import pooltool.constants as c
import pooltool.physics as physics
from pooltool.events.datatypes import Agent, Event, EventType
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.cue.datatypes import Cue
from pooltool.objects.datatypes import NullObject
from pooltool.objects.table.components import (
    CircularCushionSegment,
    LinearCushionSegment,
    Pocket,
)


def null_event(time: float) -> Event:
    return Event(
        event_type=EventType.NONE,
        agents=(Agent.from_object(NullObject()),),
        time=time,
    )


def ball_ball_collision(ball1: Ball, ball2: Ball, time: float) -> Event:
    return Event(
        event_type=EventType.BALL_BALL,
        agents=(
            Agent.from_object(ball1),
            Agent.from_object(ball2),
        ),
        time=time,
    )


def ball_linear_cushion_collision(
    ball: Ball, cushion: LinearCushionSegment, time: float
) -> Event:
    return Event(
        event_type=EventType.BALL_LINEAR_CUSHION,
        agents=(
            Agent.from_object(ball),
            Agent.from_object(cushion),
        ),
        time=time,
    )


def ball_circular_cushion_collision(
    ball: Ball, cushion: CircularCushionSegment, time: float
) -> Event:
    return Event(
        event_type=EventType.BALL_CIRCULAR_CUSHION,
        agents=(Agent.from_object(ball), Agent.from_object(cushion)),
        time=time,
    )


def ball_pocket_collision(ball: Ball, pocket: Pocket, time: float) -> Event:
    return Event(
        event_type=EventType.BALL_POCKET,
        agents=(
            Agent.from_object(ball),
            Agent.from_object(pocket),
        ),
        time=time,
    )


def stick_ball_collision(stick: Cue, ball: Ball, time: float) -> Event:
    return Event(
        event_type=EventType.STICK_BALL,
        agents=(
            Agent.from_object(stick),
            Agent.from_object(ball),
        ),
        time=time,
    )


def spinning_stationary_transition(ball: Ball, time: float) -> Event:
    return Event(
        event_type=EventType.SPINNING_STATIONARY,
        agents=(Agent.from_object(ball),),
        time=time,
    )


def rolling_stationary_transition(ball: Ball, time: float) -> Event:
    return Event(
        event_type=EventType.ROLLING_STATIONARY,
        agents=(Agent.from_object(ball),),
        time=time,
    )


def rolling_spinning_transition(ball: Ball, time: float) -> Event:
    return Event(
        event_type=EventType.ROLLING_SPINNING,
        agents=(Agent.from_object(ball),),
        time=time,
    )


def sliding_rolling_transition(ball: Ball, time: float) -> Event:
    return Event(
        event_type=EventType.SLIDING_ROLLING,
        agents=(Agent.from_object(ball),),
        time=time,
    )
