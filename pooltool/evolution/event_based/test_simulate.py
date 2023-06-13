import numpy as np
import pytest
from numpy.typing import NDArray

import pooltool.constants as const
import pooltool.math as math
import pooltool.physics as physics
from pooltool.events import Event, EventType, ball_ball_collision, ball_pocket_collision
from pooltool.evolution.event_based.simulate import (
    get_next_ball_ball_collision,
    get_next_event,
    simulate,
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


def _assert_rolling(rvw: NDArray[np.float64], R: float) -> None:
    assert np.isclose(physics.rel_velocity(rvw, R), 0).all()


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
    template = System(
        cue=Cue.default(),
        table=(table := Table.default()),
        balls={
            "1": (ball := Ball.create("1", xy=(table.w / 2, table.l / 2))),
            "cue": Ball.create(
                "cue", xy=(table.w / 2 + 2 * ball.params.R, table.l / 2 - 1)
            ),
        },
    )

    def _move_cue(system: System, phi: float) -> None:
        v = np.array(
            [
                0.5 * np.cos(phi * np.pi / 180),
                0.5 * np.sin(phi * np.pi / 180),
                0,
            ]
        )
        w = math.cross(np.array([0, 0, 1]), v) / ball.params.R

        system.balls["cue"].state.rvw[1] = v
        system.balls["cue"].state.rvw[2] = w
        system.balls["cue"].state.s = const.rolling

        # The cue is truly rolling
        _assert_rolling(system.balls["cue"].state.rvw, system.balls["cue"].params.R)

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

        root = min_real_root(coeffs_array)[0]

        if phi < 90:
            assert root == np.inf
        if phi > 90:
            assert root != np.inf


@pytest.mark.parametrize("solver", [QuarticSolver.NUMERIC, QuarticSolver.HYBRID])
def test_touching_ball_ball_collision(solver: QuarticSolver):
    """A hit with two touching/almost touching balls

    In this example, a cue ball is hit into the 1 ball at point blank with various
    states and the existence of the collision is asserted.

            , - ~  ,                 , - ~  ,
        , '          ' ,         , '          ' ,
      ,                  ,     ,                  ,
     ,                    ,   ,                    ,
    ,                      , ,                      ,
    ,          one         , ,      <---cue         ,
    ,                      , ,                      ,
     ,                    ,   ,                    ,
      ,                  ,     ,                  ,
        ,               '        ,               '
          ' - , _ , - '            ' - , _ , - '
    """
    template = System(
        cue=Cue.default(),
        table=(table := Table.default()),
        balls={
            "1": (ball := Ball.create("1", xy=(table.w / 2, table.l / 2))),
            "cue": Ball.create(
                "cue", xy=(table.w / 2 + 2 * ball.params.R, table.l / 2)
            ),
        },
    )

    def _apply_parameters(system: System, V0: float, eps: float) -> None:
        rx = table.w / 2 + 2 * ball.params.R + eps
        v = np.array(
            [
                -V0,
                0,
                0,
            ]
        )
        w = math.cross(np.array([0, 0, 1]), v) / ball.params.R

        system.balls["cue"].state.rvw[0, 0] = rx
        system.balls["cue"].state.rvw[1] = v
        system.balls["cue"].state.rvw[2] = w
        system.balls["cue"].state.s = const.rolling

        # The cue is truly rolling
        _assert_rolling(system.balls["cue"].state.rvw, ball.params.R)

    def true_time_to_collision(eps, V0, mu_r, g):
        """Return the correct time until collision

        Due to the specific setup, the real collision time is a simple high school
        physics problem:

        rx(t) = r0x - V0 * t + 1/2 * mu_r * g * t**2

        Solve for tf, where rx(tf) = 2 * R and r0x = 2 * R + eps
        """
        collision_time = np.inf
        for t in math.quadratic.solve(0.5 * mu_r * g, -V0, eps):
            if t >= 0 and t < collision_time:
                collision_time = t
        return collision_time

    V0 = 2
    for eps in np.logspace(-12, -1, 20):
        system = template.copy()
        _apply_parameters(system, V0, eps)

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

        # NOTE This is missing actual tests, or perhaps this test should be deleted. So
        # far I've been using this as a playground to compare the different methods

        numeric = min_real_root(coeffs_array, solver=QuarticSolver.NUMERIC)[0]
        newton = -coeffs[-1] / coeffs[-2]
        truth = true_time_to_collision(eps, V0, ball1.params.u_r, ball1.params.g)
        hybrid = min_real_root(coeffs_array, solver=QuarticSolver.HYBRID)[0]
        pct_diff = lambda x: f"{(abs(x - truth) / truth * 100):.4f}"
        print(f"-- {eps=}")
        print(f" Truth: {truth}")
        print(f" Newton (% diff): {pct_diff(newton)}%")
        print(f" Hybrid (% diff): {pct_diff(hybrid)}%")
        print(f" Numeric (% diff): {pct_diff(numeric)}%")


@pytest.mark.parametrize("solver", [QuarticSolver.NUMERIC, QuarticSolver.HYBRID])
def test_no_ball_ball_collisions_for_intersecting_balls(solver: QuarticSolver):
    """Two already intersecting balls don't collide

    In this instance, no further collision is detected because the balls are already
    intersecting. Otherwise perpetual internal collisions occur, keeping the two balls
    locked.

    This test doesn't make sure that balls don't intersect, it tests the safeguard that
    prevents already intersecting balls from colliding with their internal walls, which
    keeps them intersected like links in a chain.

            , - ~  ,        , - ~  ,
        , '          ' ,, '          ' ,
      ,               ,   ,              ,
     ,               ,     ,              ,
    ,               ,       ,              ,
    ,          one  ,       , <--cue       ,
    ,               ,       ,              ,
     ,               ,     ,              ,
      ,               ,   ,              ,
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

    v = np.array([-0.5, 0, 0])
    w = math.cross(np.array([0, 0, 1]), v) / ball.params.R

    system.balls["cue"].state.rvw[1] = v
    system.balls["cue"].state.rvw[2] = w
    system.balls["cue"].state.s = const.rolling

    # The cue is truly rolling
    _assert_rolling(system.balls["cue"].state.rvw, system.balls["cue"].params.R)

    assert (
        get_next_event(system, quartic_solver=solver).event_type != EventType.BALL_BALL
    )
    assert get_next_ball_ball_collision(system, solver=solver).time == np.inf
