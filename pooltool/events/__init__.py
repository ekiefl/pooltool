"""Event, detection, and filtration

See `here <https://ekiefl.github.io/2020/12/20/pooltool-alg/#2-what-are-events>`_ to
learn about events and why they matter.
"""

from pooltool.events.datatypes import Agent, AgentType, Event, EventType
from pooltool.events.factory import (
    ball_ball_collision,
    ball_circular_cushion_collision,
    ball_linear_cushion_collision,
    ball_pocket_collision,
    null_event,
    rolling_spinning_transition,
    rolling_stationary_transition,
    sliding_rolling_transition,
    spinning_stationary_transition,
    stick_ball_collision,
)
from pooltool.events.filter import (
    by_ball,
    by_time,
    by_type,
    filter_ball,
    filter_events,
    filter_time,
    filter_type,
)

__all__ = [
    "filter_ball",
    "filter_time",
    "filter_type",
    "filter_events",
    "by_type",
    "by_ball",
    "by_time",
    "null_event",
    "ball_ball_collision",
    "ball_linear_cushion_collision",
    "ball_circular_cushion_collision",
    "ball_pocket_collision",
    "stick_ball_collision",
    "spinning_stationary_transition",
    "rolling_stationary_transition",
    "rolling_spinning_transition",
    "sliding_rolling_transition",
    "Event",
    "EventType",
    "AgentType",
    "Agent",
]
