import numpy as np
import pytest

import pooltool.constants as const
from pooltool.events import Event, EventType, ball_ball_collision, ball_pocket_collision
from pooltool.evolution.event_based.simulate import (
    get_next_ball_ball_collision,
    get_next_event,
)
from pooltool.evolution.event_based.solve import ball_ball_collision_coeffs
from pooltool.evolution.event_based.test_data import TEST_DIR
from pooltool.math.roots import QuarticSolver, min_real_root
from pooltool.objects import Ball, BilliardTableSpecs, Cue, Table
from pooltool.system import System


@pytest.mark.parametrize("solver", [QuarticSolver.NUMERIC, QuarticSolver.HYBRID])
def test_case1(solver: QuarticSolver):
    """A case that once broke the game

    In this shot, the next event should be:

        <Event object at 0x7fe42a948b80>
         ├── type   : ball_ball
         ├── time   : 0.048943195
         └── agents : ['1', 'cue']
    """

    shot = System.load(TEST_DIR / "case1.msgpack")
    for ball in shot.balls.values():
        ball.state = ball.history[0]
    shot.reset_history()

    next_event = get_next_event(shot, solver)

    expected = ball_ball_collision(
        shot.balls["1"], shot.balls["cue"], 0.048943195217641386
    )
    assert next_event.agents == expected.agents
    assert next_event.time == pytest.approx(expected.time, abs=1e-9)


@pytest.mark.parametrize("solver", [QuarticSolver.NUMERIC, QuarticSolver.HYBRID])
def test_case2(solver: QuarticSolver):
    """A case that once broke the game

    In this shot, the next event should be:

        <Event object at 0x7fc1a3164a80>
         ├── type   : ball_pocket
         ├── time   : 0.089330336
         └── agents : ['8', 'lc']
    """
    shot = System.load(TEST_DIR / "case2.msgpack")

    next_event = get_next_event(shot, solver)

    expected = ball_pocket_collision(
        shot.balls["8"], shot.table.pockets["lc"], 0.08933033587481054
    )

    assert next_event.agents == expected.agents
    assert next_event.time == pytest.approx(expected.time, abs=1e-9)


@pytest.mark.parametrize("solver", [QuarticSolver.NUMERIC, QuarticSolver.HYBRID])
def test_case3(solver: QuarticSolver):
    """A case that the HYBRID solver struggles with

    In this shot, the next event should be:

        <Event object at 0x7ff54a6bd940>
         ├── type   : ball_ball
         ├── time   : 0.000005810
         └── agents : ['2', '5']

    The other observed candidate was

        <Event object at 0x7ff54a70f840>
         ├── type   : ball_ball
         ├── time   : 0.000006211
         └── agents : ['6', '8']

    However, if this event is chosen, balls 2 and 5 end up intersecting.
    """

    shot = System.load(TEST_DIR / "case3.msgpack")

    ball1 = shot.balls["2"]
    ball2 = shot.balls["5"]

    event = get_next_event(shot, quartic_solver=solver)

    coeffs = ball_ball_collision_coeffs(
        rvw1=ball1.state.rvw,
        rvw2=ball2.state.rvw,
        s1=ball1.state.s,
        s2=ball2.state.s,
        mu1=(ball1.params.u_s if ball1.state.s == const.sliding else ball1.params.u_r),
        mu2=(ball2.params.u_s if ball2.state.s == const.sliding else ball2.params.u_r),
        m1=ball1.params.m,
        m2=ball2.params.m,
        g1=ball1.params.g,
        g2=ball2.params.g,
        R=ball1.params.R,
    )

    coeffs_array = np.array([coeffs], dtype=np.float64)

    expected = pytest.approx(5.810383731499328e-06, abs=1e-9)

    if solver == QuarticSolver.NUMERIC:
        assert event.time == expected
        assert min_real_root(coeffs_array, solver=solver)[0] == expected
    elif solver == QuarticSolver.HYBRID:
        # THIS IS A SHORTCOMING OF THE HYBRD MODEL. It sees the wrong next event because
        # the calculated root with the analytical formula fails to have a rtol < 1e-3
        # (the actual value is like 3e-3).
        assert event.time != expected
        assert min_real_root(coeffs_array, solver=solver)[0] != expected


@pytest.mark.parametrize("solver", [QuarticSolver.NUMERIC, QuarticSolver.HYBRID])
def test_grazing_ball_ball_collision(solver: QuarticSolver):
    """A very narrow hit

    In this example, a cue ball is hit in the direction pictured below. In one case, phi
    is just short of 90 degrees, resulting in no collision. In the second case, phi is
    just long of 90 degrees, resulting in a collision. Our quartic solvers must be able
    to distinguish between these two scenarios.

            , - ~  ,         |
        , '          ' ,
      ,                  ,   |
     ,                    ,
    ,                      , |
    ,          one         ,
    ,                      , |
     ,                    ,
      ,                  ,   |
        ,               '             , - ~  ,
          ' - , _ , - '      |    , '          ' ,
                                ,         ^        ,
                             | ,          |         ,
                              ,           |          ,
                             |,          cue         ,
                              ,                      ,
                             | ,                    ,
                                ,                  ,
                             |    ,               '
                                    ' - , _ , - '
                             |
    """
    R = 0.028575
    template = System(
        cue=Cue.default(),
        table=(table := Table.default()),
        balls={
            "cue": Ball.create("cue", xy=(table.w / 2 + 2 * R, table.l / 2 - 1)),
            "1": Ball.create("1", xy=(table.w / 2, table.l / 2)),
        },
    )

    for phi in np.linspace(89.999, 90.001, 20):
        system = template.copy()
        _move_cue(system, phi)

        ball1 = system.balls["cue"]
        ball2 = system.balls["1"]

        coeffs = ball_ball_collision_coeffs(
            rvw1=ball1.state.rvw,
            rvw2=ball2.state.rvw,
            s1=ball1.state.s,
            s2=ball2.state.s,
            mu1=(
                ball1.params.u_s if ball1.state.s == const.sliding else ball1.params.u_r
            ),
            mu2=(
                ball2.params.u_s if ball2.state.s == const.sliding else ball2.params.u_r
            ),
            m1=ball1.params.m,
            m2=ball2.params.m,
            g1=ball1.params.g,
            g2=ball2.params.g,
            R=ball1.params.R,
        )

        coeffs_array = np.array([coeffs], dtype=np.float64)

        if phi < 90:
            assert min_real_root(coeffs_array)[0] == np.inf
        if phi > 90:
            assert min_real_root(coeffs_array)[0] != np.inf


def _move_cue(system: System, phi: float) -> None:
    system.balls["cue"].state.rvw[1] = [
        0.5 * np.cos(phi * np.pi / 180),
        0.5 * np.sin(phi * np.pi / 180),
        0,
    ]
    system.balls["cue"].state.s = 3


@pytest.mark.parametrize("solver", [QuarticSolver.NUMERIC, QuarticSolver.HYBRID])
def test_no_ball_ball_collisions_for_intersecting_balls(solver: QuarticSolver):
    """Two already intersecting balls don't collide

    In this instance, no further collision is detected because the balls are already
    interesecting. Otherwise perpetual internal collisions occur, keeping the two balls
    locked.

    This test doesn't make sure that balls don't intersect, it tests the safeguard that
    prevents already intersecting balls from colliding with their internal walls, which
    keeps them intersected like links in a chain.

            , - ~  ,        , - ~  ,
        , '          ' ,, '          ' ,
      ,               ,                  ,
     ,               ,                    ,
    ,               ,                      ,
    ,          one  ,      <---cue         ,
    ,               ,                      ,
     ,               ,                    ,
      ,               ,                  ,
        ,               ,               '
          ' - , _ , - '   ' - , _ , - '
    """

    system = System(
        cue=Cue.default(),
        table=(table := Table.from_table_specs(BilliardTableSpecs(l=10, w=10))),
        balls={
            "1": (ball := Ball.create("1", xy=(table.w / 2, table.l / 2))),
            "cue": Ball.create("cue", xy=(table.w / 2 + ball.params.R, table.l / 2)),
        },
    )

    system.balls["cue"].state.rvw[1] = [-0.5, 0, 0]
    system.balls["cue"].state.s = const.rolling

    assert (
        get_next_event(system, quartic_solver=solver).event_type != EventType.BALL_BALL
    )
    assert get_next_ball_ball_collision(system, solver=solver).time == np.inf
