import attrs
import numpy as np
import pytest

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.events import EventType
from pooltool.evolution.event_based.cache import CollisionCache
from pooltool.evolution.event_based.detect.ball_ball import (
    ball_ball_collision_time_2d,
    get_next_ball_ball_event,
)
from pooltool.physics.evolve import evolve_ball_motion
from pooltool.physics.utils import get_airborne_time
from pooltool.system.datatypes import Ball, Cue, System, Table


def _make_rolling_ball(ball_id: str, xy: tuple[float, float], velocity: float) -> Ball:
    ball = Ball.create(ball_id, xy=xy)
    v = np.array([0.0, velocity, 0.0])
    w = ptmath.cross(np.array([0.0, 0.0, 1.0]), v) / ball.params.R
    ball.state.rvw[1] = v
    ball.state.rvw[2] = w
    ball.state.s = const.rolling
    return ball


@pytest.mark.parametrize("is_3d", [True, False])
def test_sliding_ball_collision_time(is_3d: bool):
    table = Table.default()
    cue = Cue.default()

    cue_ball_position = (1 / 4) * table.l
    one_ball_position = (3 / 4) * table.l
    cue_ball = Ball.create("cue", xy=(table.w / 2, cue_ball_position))
    one_ball = Ball.create("1", xy=(table.w / 2, one_ball_position))

    distance = abs(one_ball_position - cue_ball_position) - (
        cue_ball.params.R + one_ball.params.R
    )
    speed = 5

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

    # Constant sliding deceleration a = u_s*g.  d = speed*t - 0.5*a*t**2  =>  smaller
    # positive root gives the collision time.
    a = cue_ball.params.u_s * cue_ball.params.g
    expected = (speed - np.sqrt(speed**2 - 2 * a * distance)) / a

    assert np.isclose(actual, expected), f"actual={actual}, expected={expected}"


@pytest.mark.parametrize("is_3d", [True, False])
def test_parallel_rolling_balls_do_not_collide(is_3d: bool):
    """Parallel rolling balls at fixed separation never collide."""

    table = Table.default()
    cue = Cue.default()

    cue_ball = _make_rolling_ball("cue", (table.w / 2, table.l / 4), velocity=1.0)
    one_ball = _make_rolling_ball("1", (table.w / 2, 3 * table.l / 4), velocity=1.0)

    system = System(
        cue=cue,
        table=table,
        balls={
            "cue": cue_ball,
            "1": one_ball,
        },
    )

    event = get_next_ball_ball_event(system, CollisionCache(), is_3d=is_3d)
    assert event.time == np.inf

    if not is_3d:
        actual = ball_ball_collision_time_2d(
            rvw1=cue_ball.state.rvw,
            rvw2=one_ball.state.rvw,
            s1=cue_ball.state.s,
            s2=one_ball.state.s,
            mu1=cue_ball.params.u_r,
            mu2=one_ball.params.u_r,
            m1=cue_ball.params.m,
            m2=one_ball.params.m,
            g1=cue_ball.params.g,
            g2=one_ball.params.g,
            R=cue_ball.params.R,
        )
        assert actual == np.inf


def test_parallel_rolling_balls_collide_from_quadratic_root_2d():
    """The 2D detector handles finite roots when the quartic term is zero."""

    table = Table.default()
    cue = Cue.default()

    cue_ball = _make_rolling_ball("cue", (table.w / 2, table.l / 4), velocity=2.0)
    R = cue_ball.params.R
    center_gap = 4 * R
    one_ball = _make_rolling_ball(
        "1",
        (table.w / 2, table.l / 4 + center_gap),
        velocity=1.0,
    )

    system = System(
        cue=cue,
        table=table,
        balls={
            "cue": cue_ball,
            "1": one_ball,
        },
    )

    expected = (center_gap - 2 * R) / (
        cue_ball.state.rvw[1, 1] - one_ball.state.rvw[1, 1]
    )

    event = get_next_ball_ball_event(system, CollisionCache(), is_3d=False)
    assert np.isclose(event.time, expected)


@pytest.mark.parametrize(
    ("cue_velocity", "one_velocity", "expected"),
    [
        (2.0, 1.0, 0.0),
        (1.0, 1.0, np.inf),
        (1.0, 2.0, np.inf),
    ],
)
@pytest.mark.parametrize("is_3d", [True, False])
def test_tangent_parallel_rolling_balls_only_collide_when_closing(
    cue_velocity: float,
    one_velocity: float,
    expected: float,
    is_3d: bool,
):
    table = Table.default()
    cue = Cue.default()

    cue_ball = _make_rolling_ball("cue", (0.0, 0.0), velocity=cue_velocity)
    one_ball = _make_rolling_ball(
        "1",
        (0.0, 2 * cue_ball.params.R),
        velocity=one_velocity,
    )

    system = System(
        cue=cue,
        table=table,
        balls={
            "cue": cue_ball,
            "1": one_ball,
        },
    )

    direct = ball_ball_collision_time_2d(
        rvw1=cue_ball.state.rvw,
        rvw2=one_ball.state.rvw,
        s1=cue_ball.state.s,
        s2=one_ball.state.s,
        mu1=cue_ball.params.u_r,
        mu2=one_ball.params.u_r,
        m1=cue_ball.params.m,
        m2=one_ball.params.m,
        g1=cue_ball.params.g,
        g2=one_ball.params.g,
        R=cue_ball.params.R,
    )
    event = get_next_ball_ball_event(system, CollisionCache(), is_3d=is_3d)

    if expected == np.inf:
        assert direct == np.inf
        assert event.time == np.inf
    else:
        assert direct == expected
        assert event.time == expected


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


def test_rolling_balls_uneven_radii_collision_geometry():
    """Two rolling balls of different radii collide at a slanted line of centers.

    Note:
        - ``System`` currently asserts equal radii via an attrs field validator. Until
          that validator is removed (and unequal radii are supported), we construct the
          system inside ``attrs.validators.disabled()``

                          , - ~  ,
                      , '          ' ,
                    ,                  ,
                   ,                    ,
                  ,                      ,
        *  *      ,      <--one          ,
     *        *   ,                      ,
    *   cue->  *   ,                    ,
    *          *    ,                  ,
     *        *       ,               '
        *  *            ' - , _ , - '
    --------------------------------------
                   table
    """
    table = Table.default()
    cue = Cue.default()

    R1 = 0.02
    R2 = 0.04

    ball1 = Ball.create("cue", xy=(table.w / 2 - 0.3, table.l / 2), R=R1)
    ball2 = Ball.create("1", xy=(table.w / 2 + 0.3, table.l / 2), R=R2)

    v1 = np.array([1.0, 0.0, 0.0])
    v2 = np.array([-1.0, 0.0, 0.0])

    ball1.state.rvw[1] = v1
    ball1.state.rvw[2] = ptmath.cross(np.array([0, 0, 1]), v1) / R1
    ball1.state.s = const.rolling

    ball2.state.rvw[1] = v2
    ball2.state.rvw[2] = ptmath.cross(np.array([0, 0, 1]), v2) / R2
    ball2.state.s = const.rolling

    with attrs.validators.disabled():
        system = System(
            cue=cue,
            table=table,
            balls={"cue": ball1, "1": ball2},
        )

    event = get_next_ball_ball_event(system, CollisionCache(), is_3d=True)
    assert event.event_type == EventType.BALL_BALL
    t = event.time
    assert np.isfinite(t), f"expected a finite collision time, got {t}"

    rvw1_f, _ = evolve_ball_motion(
        ball1.state.s,
        ball1.state.rvw,
        ball1.params.R,
        ball1.params.m,
        ball1.params.u_s,
        ball1.params.u_sp,
        ball1.params.u_r,
        ball1.params.g,
        t,
    )
    rvw2_f, _ = evolve_ball_motion(
        ball2.state.s,
        ball2.state.rvw,
        ball2.params.R,
        ball2.params.m,
        ball2.params.u_s,
        ball2.params.u_sp,
        ball2.params.u_r,
        ball2.params.g,
        t,
    )

    pos1 = rvw1_f[0]
    pos2 = rvw2_f[0]

    xy_dist = float(np.linalg.norm(pos1[:2] - pos2[:2]))
    dist_3d = float(np.linalg.norm(pos1 - pos2))

    # At contact: xy_dist**2 + (R2 - R1)**2 = (R1 + R2)**2  =>  xy_dist = 2 * sqrt(R1 * R2)
    expected_xy_dist = 2 * np.sqrt(R1 * R2)
    assert np.isclose(xy_dist, expected_xy_dist), (
        f"xy_dist={xy_dist} should equal 2*sqrt(R1*R2)={expected_xy_dist}"
    )
    assert np.isclose(dist_3d, R1 + R2), (
        f"dist_3d={dist_3d} should equal R1+R2={R1 + R2}"
    )
