from typing import Tuple

import numpy as np
import pytest

import pooltool.constants as const
from pooltool.events import (
    ball_ball_collision,
    ball_linear_cushion_collision,
    ball_pocket_collision,
    stick_ball_collision,
)
from pooltool.objects import Ball, Cue, LinearCushionSegment, Pocket
from pooltool.physics.engine import PhysicsEngine

ENGINE = PhysicsEngine()


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


@pytest.fixture
def cue_colliding_with_pocket() -> Tuple[Ball, Pocket]:
    """Return ball and pocket at the point of collision"""

    # Create ball and linear cushion segment
    cue = Ball.create("cue", xy=(1, 0), R=1)
    cue.state.rvw[1] = (-1, 0, 0)
    pocket = Pocket("pocket", center=np.array([0, 0, 0]), radius=1)

    return cue, pocket


@pytest.fixture
def cue_struck_by_cuestick() -> Tuple[Cue, Ball]:
    """Return cuestick and ball"""

    cue = Ball.create("cue", xy=(0, 0), R=1)
    stick = Cue()

    stick.set_state(V0=1, phi=0)

    return stick, cue


def test_ball_ball_collision(cue_colliding_into_one_ball):
    event = ball_ball_collision(*cue_colliding_into_one_ball, time=0, set_initial=True)

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
    event = ENGINE.resolve_event(event)

    # Cue ball initial
    assert np.array_equal(event.agents[0].get_initial().state.rvw, cue_initial_expected)

    # Cue ball final
    cue_final_expected = np.array([[-2, 0, 1], [0, 0, 0], [0, 0, 0]])
    assert (
        np.isclose(
            event.agents[0].get_final().state.rvw,
            cue_final_expected,
            atol=const.EPS_SPACE + const.EPS,
        )
    ).all()

    # One ball initial
    assert np.array_equal(event.agents[1].get_initial().state.rvw, one_initial_expected)

    # One ball final
    one_final_expected = np.array([[0, 0, 1], [1, 0, 0], [0, 0, 0]])
    assert (
        np.isclose(
            event.agents[1].get_final().state.rvw,
            one_final_expected,
            atol=const.EPS_SPACE + const.EPS,
        )
    ).all()


def test_ball_linear_cushion_collision(cue_colliding_into_cushion):
    event = ball_linear_cushion_collision(
        *cue_colliding_into_cushion, time=0, set_initial=True
    )

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
    event = ENGINE.resolve_event(event)

    # Cue ball initial
    assert np.array_equal(event.agents[0].get_initial().state.rvw, cue_initial_expected)

    # Cue ball final
    assert event.agents[0].get_final() is not None

    # Cushion initial
    assert event.agents[1].get_initial() == cue_colliding_into_cushion[1]

    # Cushion final remains None because it's assumed to be constant
    assert event.agents[1].get_final() is None


def test_ball_pocket_collision(cue_colliding_with_pocket):
    ball, pocket = cue_colliding_with_pocket
    event = ball_pocket_collision(ball, pocket, time=0, set_initial=True)

    # Before the resolution, the initial states should be set and the final states
    # shouldn't be

    # Cue ball initial
    cue_initial_expected = np.array([[1, 0, 1], [-1, 0, 0], [0, 0, 0]])
    assert np.array_equal(event.agents[0].get_initial().state.rvw, cue_initial_expected)

    # Cue ball final
    assert event.agents[0].get_final() is None

    # Pocket initial
    assert event.agents[1].get_initial().contains == set()

    # Pocket final
    assert event.agents[1].get_final() is None

    # Now resolve the event and re-assess
    event = ENGINE.resolve_event(event)

    # Cue ball initial
    assert np.array_equal(event.agents[0].get_initial().state.rvw, cue_initial_expected)

    # Cue ball final
    expected_pos = np.array([pocket.center[0], pocket.center[1], -pocket.depth])
    assert np.array_equal(event.agents[0].get_final().state.rvw[0], expected_pos)

    # Pocket initial
    assert event.agents[1].get_initial().contains == set()

    # Pocket final
    assert event.agents[1].get_final().contains == {"cue"}


def test_stick_ball_collision(cue_struck_by_cuestick):
    stick, cue = cue_struck_by_cuestick

    event = stick_ball_collision(stick, cue, time=0, set_initial=True)

    # Before the resolution, the initial states should be set and the final states
    # shouldn't be

    # Cue ball initial
    cue_initial_expected = np.array([[0, 0, 1], [0, 0, 0], [0, 0, 0]])
    assert np.array_equal(event.agents[1].get_initial().state.rvw, cue_initial_expected)

    # Cue ball final
    assert event.agents[1].get_final() is None

    # Stick initial
    assert event.agents[0].get_initial() == stick
    assert event.agents[0].get_initial() is not stick

    # Stick final
    assert event.agents[0].get_final() is None

    # Now resolve the event and re-assess
    event = ENGINE.resolve_event(event)

    # Cue ball initial
    assert np.array_equal(event.agents[1].get_initial().state.rvw, cue_initial_expected)

    # Cue ball final
    rvw_final = event.agents[1].get_final().state.rvw
    assert np.array_equal(rvw_final[0], cue_initial_expected[0])

    # Stick initial
    assert event.agents[0].get_initial() == stick
    assert event.agents[0].get_initial() is not stick

    # Stick final
    assert event.agents[0].get_final() is None
