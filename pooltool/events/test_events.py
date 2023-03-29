from typing import Tuple

import numpy as np
import pytest

from pooltool.events import (
    ball_ball_collision,
    ball_linear_cushion_collision,
    resolve_event,
)
from pooltool.objects import Ball, LinearCushionSegment


@pytest.fixture
def cue_colliding_into_one_ball() -> Tuple[Ball, Ball]:
    """Return two balls at the point of collision

            , - ~  ,                , - ~  ,
        , '          ' ,        , '          ' ,
      ,                  ,    ,                  ,
     ,                    ,  ,                    ,
    ,                      ,,                      ,
    ,          cue ---->   ,,          one         ,
    ,                      ,,                      ,
     ,                    ,  ,                    ,
      ,                  ,    ,                  ,
        ,               '       ,               '
          ' - , _ , - '           ' - , _ , - '
    """

    # Create the balls each with radius 1, cue ball is left of one ball
    cue = Ball.create("cue", xy=(-2, 0), R=1)
    one = Ball.create("1", xy=(0, 0), R=1)

    # The cue ball is moving in +x direction with velocity 1
    cue.state.rvw[1] = (1, 0, 0)

    return cue, one


@pytest.fixture
def cue_colliding_into_cushion() -> Tuple[Ball, LinearCushionSegment]:
    """Return ball and cushion at the point of collision

            |        , - ~  ,
            |    , '          ' ,
            |  ,                  ,
            | ,                    ,
            |,                      ,
    cushion |,    <---- cue         ,
            |,                      ,
            | ,                    ,
            |  ,                  ,
            |    ,               '
            |      ' - , _ , - '
            |
    """

    # Create ball and linear cushion segment
    cue = Ball.create("cue", xy=(1, 0), R=1)
    cue.state.rvw[1] = (-1, 0, 0)
    cushion = LinearCushionSegment(
        "cushion", p1=np.array([0, -1, 0.6]), p2=np.array([0, 1, 0.6])
    )

    return cue, cushion


def test_ball_ball_collision(cue_colliding_into_one_ball):
    event = ball_ball_collision(*cue_colliding_into_one_ball, time=0)

    # Before the resolution, the initial states should be set and the final states
    # shouldn't be

    # Cue ball initial
    cue_initial_expected = np.array([[-2, 0, 1], [1, 0, 0], [0, 0, 0]])
    assert np.array_equal(event.agents[0].get_initial().state.rvw, cue_initial_expected)

    # Cue ball final
    assert event.agents[0].get_final() is None

    # One ball initial
    one_initial_expected = np.array([[0, 0, 1], [0, 0, 0], [0, 0, 0]])
    assert np.array_equal(event.agents[1].get_initial().state.rvw, one_initial_expected)

    # One ball final
    assert event.agents[1].get_final() is None

    # Now resolve the event and re-assess
    event = resolve_event(event)

    # Cue ball initial
    assert np.array_equal(event.agents[0].get_initial().state.rvw, cue_initial_expected)

    # Cue ball final
    cue_final_expected = np.array([[-2, 0, 1], [0, 0, 0], [0, 0, 0]])
    assert np.array_equal(event.agents[0].get_final().state.rvw, cue_final_expected)

    # One ball initial
    assert np.array_equal(event.agents[1].get_initial().state.rvw, one_initial_expected)

    # One ball final
    one_final_expected = np.array([[0, 0, 1], [1, 0, 0], [0, 0, 0]])
    assert np.array_equal(event.agents[1].get_final().state.rvw, one_final_expected)


def test_ball_linear_cushion_collision(cue_colliding_into_cushion):
    event = ball_linear_cushion_collision(*cue_colliding_into_cushion, time=0)

    # Before the resolution, the initial states should be set and the final states
    # shouldn't be

    # Cue ball initial
    cue_initial_expected = np.array([[1, 0, 1], [-1, 0, 0], [0, 0, 0]])
    assert np.array_equal(event.agents[0].get_initial().state.rvw, cue_initial_expected)

    # Cue ball final
    assert event.agents[0].get_final() is None

    # Cushion initial
    assert event.agents[1].get_initial() == cue_colliding_into_cushion[1]

    # Cushion final
    assert event.agents[1].get_final() is None

    # Now resolve the event and re-assess
    event = resolve_event(event)

    # Cue ball initial
    assert np.array_equal(event.agents[0].get_initial().state.rvw, cue_initial_expected)
    assert event.agents[0].get_final() is not None

    # Cushion initial
    assert event.agents[1].get_initial() == cue_colliding_into_cushion[1]

    # Cushion final remains None because it's assumed to be constant
    assert event.agents[1].get_final() is None
