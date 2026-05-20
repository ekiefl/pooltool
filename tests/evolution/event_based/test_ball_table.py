import numpy as np
import pytest

import pooltool.constants as const
from pooltool.events import EventType
from pooltool.evolution.event_based.cache import CollisionCache
from pooltool.evolution.event_based.detect.ball_table import (
    get_next_ball_table_event,
)
from pooltool.physics.utils import get_airborne_time
from pooltool.system.datatypes import System


@pytest.fixture
def system() -> System:
    return System.example()


def test_no_airborne_balls_returns_inf_time(system: System):
    """In a default 2D scene no ball is airborne, so the emitted event has time=inf."""
    event = get_next_ball_table_event(system, CollisionCache())
    assert event.event_type == EventType.BALL_TABLE
    assert event.time == np.inf


def test_airborne_ball_returns_finite_time(system: System):
    """An airborne ball at apex over the table returns the physics-derived drop time."""
    ball = next(iter(system.balls.values()))
    ball.state.rvw[0, 2] = ball.params.R + 0.1
    ball.state.rvw[1, 2] = 0.0
    ball.state.s = const.airborne

    event = get_next_ball_table_event(system, CollisionCache())

    expected = get_airborne_time(ball.state.rvw, ball.params.R, ball.params.g)
    assert event.event_type == EventType.BALL_TABLE
    assert event.time == pytest.approx(expected)


def test_returns_soonest_ball(system: System):
    """When multiple balls are airborne, the one with the shortest drop time wins."""
    balls = list(system.balls.values())
    assert len(balls) >= 2

    high, low = balls[0], balls[1]

    high.state.rvw[0, 2] = high.params.R + 0.5
    high.state.rvw[1, 2] = 0.0
    high.state.s = const.airborne

    low.state.rvw[0, 2] = low.params.R + 0.05
    low.state.rvw[1, 2] = 0.0
    low.state.s = const.airborne

    event = get_next_ball_table_event(system, CollisionCache())

    assert event.event_type == EventType.BALL_TABLE
    assert event.ids[0] == low.id
