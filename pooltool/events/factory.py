"""Abstracted functions for easy event creation

This submodule provides a collection of factory functions for creating Event objects.

Each function is designed to encapsulate the creation of specific types of events, such
as collisions between balls, collisions between balls and cushions, and various
transitions in the ball's state (e.g., from rolling to stationary, spinning to rolling).
"""

from __future__ import annotations

from pooltool.events.datatypes import Agent, Event, EventType
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.cue.datatypes import Cue
from pooltool.objects.datatypes import NullObject
from pooltool.objects.table.components import (
    CircularCushionSegment,
    LinearCushionSegment,
    Pocket,
)


def null_event(time: float, set_initial: bool = False) -> Event:
    """Create a null event."""
    return Event(
        event_type=EventType.NONE,
        agents=(Agent.from_object(NullObject(), set_initial=set_initial),),
        time=time,
    )


def ball_ball_collision(
    ball1: Ball, ball2: Ball, time: float, set_initial: bool = False
) -> Event:
    """Create a ball-ball collision."""
    return Event(
        event_type=EventType.BALL_BALL,
        agents=(
            Agent.from_object(ball1, set_initial=set_initial),
            Agent.from_object(ball2, set_initial=set_initial),
        ),
        time=time,
    )


def ball_linear_cushion_collision(
    ball: Ball, cushion: LinearCushionSegment, time: float, set_initial: bool = False
) -> Event:
    """Create a ball-linear-cushion collision."""
    return Event(
        event_type=EventType.BALL_LINEAR_CUSHION,
        agents=(
            Agent.from_object(ball, set_initial=set_initial),
            Agent.from_object(cushion, set_initial=set_initial),
        ),
        time=time,
    )


def ball_circular_cushion_collision(
    ball: Ball, cushion: CircularCushionSegment, time: float, set_initial: bool = False
) -> Event:
    """Create a ball-circular-cushion collision."""
    return Event(
        event_type=EventType.BALL_CIRCULAR_CUSHION,
        agents=(
            Agent.from_object(ball, set_initial=set_initial),
            Agent.from_object(cushion, set_initial=set_initial),
        ),
        time=time,
    )


def ball_pocket_collision(
    ball: Ball, pocket: Pocket, time: float, set_initial: bool = False
) -> Event:
    """Create a ball-pocket collision."""
    return Event(
        event_type=EventType.BALL_POCKET,
        agents=(
            Agent.from_object(ball, set_initial=set_initial),
            Agent.from_object(pocket, set_initial=set_initial),
        ),
        time=time,
    )


def stick_ball_collision(
    stick: Cue, ball: Ball, time: float, set_initial: bool = False
) -> Event:
    """Create a cue stick-ball collision."""
    return Event(
        event_type=EventType.STICK_BALL,
        agents=(
            Agent.from_object(stick, set_initial=set_initial),
            Agent.from_object(ball, set_initial=set_initial),
        ),
        time=time,
    )


def spinning_stationary_transition(
    ball: Ball, time: float, set_initial: bool = False
) -> Event:
    """Create a spinning-stationary transition."""
    return Event(
        event_type=EventType.SPINNING_STATIONARY,
        agents=(Agent.from_object(ball, set_initial=set_initial),),
        time=time,
    )


def rolling_stationary_transition(
    ball: Ball, time: float, set_initial: bool = False
) -> Event:
    """Create a rolling-stationary transition."""
    return Event(
        event_type=EventType.ROLLING_STATIONARY,
        agents=(Agent.from_object(ball, set_initial=set_initial),),
        time=time,
    )


def rolling_spinning_transition(
    ball: Ball, time: float, set_initial: bool = False
) -> Event:
    """Create a rolling-spinning transition."""
    return Event(
        event_type=EventType.ROLLING_SPINNING,
        agents=(Agent.from_object(ball, set_initial=set_initial),),
        time=time,
    )


def sliding_rolling_transition(
    ball: Ball, time: float, set_initial: bool = False
) -> Event:
    """Create a sliding-rolling transition."""
    return Event(
        event_type=EventType.SLIDING_ROLLING,
        agents=(Agent.from_object(ball, set_initial=set_initial),),
        time=time,
    )
