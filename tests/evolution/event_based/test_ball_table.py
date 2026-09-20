import numpy as np
import pytest
from _helpers import build_3d_engine

import pooltool.constants as const
from pooltool.events import EventType
from pooltool.evolution.event_based.cache import CollisionCache
from pooltool.evolution.event_based.detect.ball_table import (
    get_next_ball_table_event,
)
from pooltool.evolution.event_based.simulate import simulate
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.cue.datatypes import Cue
from pooltool.objects.table.datatypes import Table
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


def test_landing_on_a_ball_resolves_both_events():
    """A ball touching down exactly as it touches another ball is handled either way.

    Both events are due at once and share a priority tier. Whichever resolves first
    invalidates the other, which is recomputed from the new state and resolved when
    it is next due, which may be a hair later than the original instant.
    """
    table = Table.default()
    resting = Ball.create("resting", xy=(table.w / 2, table.l / 4))

    landing = Ball.create("landing")
    R = landing.params.R
    landing.state.rvw[0] = [table.w / 2 - 2 * R + 1e-9, table.l / 4, R]
    landing.state.rvw[1] = [1.0, 0.0, -0.5]
    landing.state.s = const.airborne

    shot = System(cue=Cue(cue_ball_id="landing"), table=table, balls=(resting, landing))
    simulate(shot, engine=build_3d_engine(), inplace=True)

    first_two = [e.event_type for e in shot.events[1:3]]
    assert set(first_two) == {EventType.BALL_TABLE, EventType.BALL_BALL}
    assert shot.events[1].time == 0.0
    assert shot.events[2].time < 1e-3
    assert shot.balls["landing"].state.s in const.on_table
    assert shot.balls["resting"].state.s in const.on_table
