import numpy as np
import pytest

import pooltool.constants as const
from pooltool.events import EventType
from pooltool.evolution.event_based.cache import CollisionCache
from pooltool.evolution.event_based.detect.ball_ball import (
    get_next_ball_ball_event,
)
from pooltool.physics.utils import get_airborne_time
from pooltool.system.datatypes import Ball, Cue, System, Table


@pytest.mark.parametrize("is_3d", [True, False])
def test_sliding_ball_collision_time(is_3d: bool):
    table = Table.default()
    cue = Cue.default()

    cue_ball_position = (1 / 4) * table.l
    one_ball_position = (3 / 4) * table.l
    cue_ball = Ball.create("cue", xy=(table.w / 2, cue_ball_position), u_s=1e-9)
    one_ball = Ball.create("1", xy=(table.w / 2, one_ball_position))

    distance = abs(one_ball_position - cue_ball_position) - (
        cue_ball.params.R + one_ball.params.R
    )
    speed = 1

    cue_ball.state.rvw[1] = speed * np.array([0, 1, 0])
    cue_ball.state.s = const.sliding

    system = System(
        cue=cue,
        table=table,
        balls={
            "cue": cue_ball,
            "1": one_ball,
        },
    )

    event = get_next_ball_ball_event(system, CollisionCache(), is_3d=is_3d)
    assert event.event_type == EventType.BALL_BALL
    actual = event.time
    expected = distance / speed
    assert np.isclose(actual, expected), f"actual={actual}, expected={expected}"


def test_airborne_balls_colliding():
    """Tests two airborne balls colliding.

                , - ~  ,                      , - ~  ,
            , '          ' ,              , '          ' ,
          ,                  ,          ,                  ,
    |    ,                    ,        ,                    ,
    |   ,                      ,      ,                      ,
    |   ,          cue--->     ,      ,      <---one         ,
    |   ,                      ,      ,                      ,
    v    ,                    ,        ,                    ,
    g     ,                  ,          ,                  ,
            ,               '             ,               '
              ' - , _ , - '                 ' - , _ , - '



        ------------------------------------------------------
                            table
    """
    table = Table.default()
    cue = Cue.default()

    cue_ball_position = (1 / 4) * table.l
    one_ball_position = (3 / 4) * table.l
    cue_ball = Ball.create("cue", xy=(table.w / 2, cue_ball_position))
    one_ball = Ball.create("1", xy=(table.w / 2, one_ball_position))

    distance = abs(one_ball_position - cue_ball_position) - (
        cue_ball.params.R + one_ball.params.R
    )
    speed = 1

    cue_ball.state.rvw[0, 2] = 100
    cue_ball.state.rvw[1] = speed * np.array([0, 1, 0])
    cue_ball.state.s = const.airborne

    one_ball.state.rvw[0, 2] = 100
    one_ball.state.s = const.airborne

    system = System(
        cue=cue,
        table=table,
        balls={
            "cue": cue_ball,
            "1": one_ball,
        },
    )

    event = get_next_ball_ball_event(system, CollisionCache(), is_3d=True)
    assert event.event_type == EventType.BALL_BALL
    actual = event.time
    expected = distance / speed
    assert np.isclose(actual, expected), f"actual={actual}, expected={expected}"


def test_ball_falls_on_top_of_ball():
    """Tests ball falling on top of other ball.

                , - ~  ,
            , '          ' ,
          ,                  ,
    |    ,                    ,
    |   ,                      ,
    |   ,          cue         ,
    |   ,           |          ,
    v    ,          v         ,
    g     ,                  ,
            ,               '
              ' - , _ , - '


                , - ~  ,
            , '          ' ,
          ,                  ,
         ,                    ,
        ,                      ,
        ,          one         ,
        ,                      ,
         ,                    ,
          ,                  ,
            ,               '
              ' - , _ , - '
        -------------------------
                  table
    """
    table = Table.default()
    cue = Cue.default()

    one_ball = Ball.create("1", xy=(table.w / 2, table.l / 2))
    one_ball.state.s = const.stationary

    cue_ball = Ball.create("cue", xy=(table.w / 2, table.l / 2))
    cue_ball.state.s = const.airborne

    # Place cue ball 10 radii above one ball
    cue_height = 10 * cue_ball.params.R
    cue_ball.state.rvw[0, 2] = cue_height

    # Since cue ball is landing on one ball instead of table, effective airborne time is
    # cue ball height minus one ball's diameter.
    rvw_shifted = cue_ball.state.rvw.copy()
    rvw_shifted[0, 2] -= 2 * one_ball.params.R
    expected_time = get_airborne_time(
        rvw_shifted,
        cue_ball.params.R,
        cue_ball.params.g,
    )

    system = System(
        cue=cue,
        table=table,
        balls={
            "cue": cue_ball,
            "1": one_ball,
        },
    )

    event = get_next_ball_ball_event(system, CollisionCache(), is_3d=True)
    assert event.event_type == EventType.BALL_BALL
    actual_time = event.time
    assert np.isclose(actual_time, expected_time), (
        f"actual={actual_time}, expected={expected_time}"
    )
