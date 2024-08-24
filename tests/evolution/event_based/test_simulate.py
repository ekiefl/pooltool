import numpy as np
import pytest
from numpy.typing import NDArray

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.events import EventType, ball_ball_collision, ball_pocket_collision
from pooltool.evolution.event_based.cache import CollisionCache
from pooltool.evolution.event_based.simulate import (
    get_next_ball_ball_collision,
    get_next_event,
    simulate,
)
from pooltool.evolution.event_based.solve import ball_ball_collision_coeffs
from pooltool.objects import Ball, BilliardTableSpecs, Cue, Table
from pooltool.ptmath.roots import quadratic, quartic
from pooltool.system import System
from tests.evolution.event_based.test_data import TEST_DIR


def test_simulate_inplace():
    # First, we don't modify in place
    system = System.example()
    simulated_system = simulate(system, inplace=False)

    # The passed system is not simulated
    assert not system.simulated

    # The returned system is
    assert simulated_system.simulated

    # The passed system is not the returned system
    assert system is not simulated_system

    # Now, we modify in place
    system = System.example()
    simulated_system = simulate(system, inplace=True)

    # The passed system is simulated
    assert system.simulated

    # The returned system is simulated
    assert simulated_system.simulated

    # The passed system is the returned system
    assert system is simulated_system


def test_simulate_continuize():
    system = System.example()
    simulate(system, inplace=True, continuous=False)

    # System is not continuized
    assert not system.continuized

    for ball in system.balls.values():
        # history_cts is empty
        assert len(ball.history_cts) == 0
        # history is not
        assert len(ball.history) > 0

    system = System.example()
    simulate(system, inplace=True, continuous=True)

    # System is continuized
    assert system.continuized

    for ball in system.balls.values():
        # history_cts is populated
        assert len(ball.history_cts) > 0
        # history is too
        assert len(ball.history) > 0


@pytest.mark.parametrize(
    "solver", [quartic.QuarticSolver.NUMERIC, quartic.QuarticSolver.HYBRID]
)
def test_case1(solver: quartic.QuarticSolver):
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

    next_event = get_next_event(shot, quartic_solver=solver)

    expected = ball_ball_collision(
        shot.balls["1"], shot.balls["cue"], 0.048943195217641386
    )
    assert next_event.agents == expected.agents
    assert next_event.time == pytest.approx(expected.time, abs=1e-9)


@pytest.mark.parametrize(
    "solver", [quartic.QuarticSolver.NUMERIC, quartic.QuarticSolver.HYBRID]
)
def test_case2(solver: quartic.QuarticSolver):
    """A case that once broke the game

    In this shot, the next event should be:

        <Event object at 0x7fc1a3164a80>
         ├── type   : ball_pocket
         ├── time   : 0.089330336
         └── agents : ['8', 'lc']
    """
    shot = System.load(TEST_DIR / "case2.msgpack")

    next_event = get_next_event(shot, quartic_solver=solver)

    expected = ball_pocket_collision(
        shot.balls["8"], shot.table.pockets["lc"], 0.08933033587481054
    )

    assert next_event.agents == expected.agents
    assert next_event.time == pytest.approx(expected.time, abs=1e-9)


@pytest.mark.parametrize(
    "solver", [quartic.QuarticSolver.NUMERIC, quartic.QuarticSolver.HYBRID]
)
def test_case3(solver: quartic.QuarticSolver):
    """A case that the HYBRID solver has struggled with

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

    assert event.time == expected
    assert quartic.solve_quartics(coeffs_array, solver=solver)[0] == expected


@pytest.mark.parametrize(
    "solver", [quartic.QuarticSolver.NUMERIC, quartic.QuarticSolver.HYBRID]
)
def test_case4(solver: quartic.QuarticSolver):
    """An UNSOLVED case that leads to a near-infinite event loop

    The infinite loop being:

        <Event object at 0x7f8714dbc5c0>
         ├── type   : ball_ball
         ├── time   : 6.991592338
         └── agents : ['5', '6']
        <Event object at 0x7f8714dbc440>
         ├── type   : sliding_rolling
         ├── time   : 6.991593919
         └── agents : ['6']
        <Event object at 0x7f8714db0700>
         ├── type   : sliding_rolling
         ├── time   : 6.991593919
         └── agents : ['5']
        <Event object at 0x7f8714dbc540>
         ├── type   : ball_ball
         ├── time   : 6.991709979
         └── agents : ['5', '7']
        <Event object at 0x7f8714db0a40>
         ├── type   : sliding_rolling
         ├── time   : 6.991710759
         └── agents : ['7']
        <Event object at 0x7f8714db0d80>
         ├── type   : rolling_stationary
         ├── time   : 6.991749764
         └── agents : ['7']
        <Event object at 0x7f8714db3200>
         ├── type   : ball_ball
         ├── time   : 6.991835060
         └── agents : ['5', '6']
        (...)

    This is not caused by overlapping balls.

    Using sandbox/break_forever.py, it tends to happen every 200 breaks or so with a cut
    angle of 45 (and not once in 4500 shots with a cut angle of 0)
    """

    shot = System.load(TEST_DIR / "case4.msgpack")  # noqa F841

    # FIXME This will go on for a very, very, very long time. To introspect, add an
    # early break after 8 events. This represents one cycle of the loop
    # simulate(shot)


def _assert_rolling(rvw: NDArray[np.float64], R: float) -> None:
    assert np.isclose(ptmath.rel_velocity(rvw, R), 0).all()


@pytest.mark.parametrize(
    "solver", [quartic.QuarticSolver.NUMERIC, quartic.QuarticSolver.HYBRID]
)
def test_grazing_ball_ball_collision(solver: quartic.QuarticSolver):
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
        w = ptmath.cross(np.array([0, 0, 1]), v) / ball.params.R

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

        root = quartic.solve_quartics(coeffs_array)[0]

        if phi < 90:
            assert root == np.inf
        if phi > 90:
            assert root != np.inf


@pytest.mark.parametrize(
    "solver", [quartic.QuarticSolver.NUMERIC, quartic.QuarticSolver.HYBRID]
)
def test_almost_touching_ball_ball_collision(solver: quartic.QuarticSolver):
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
        w = ptmath.cross(np.array([0, 0, 1]), v) / ball.params.R

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
        for t in quadratic.solve(0.5 * mu_r * g, -V0, eps):
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

        truth = true_time_to_collision(eps, V0, ball1.params.u_r, ball1.params.g)
        calculated = quartic.solve_quartics(coeffs_array, solver=solver)[0]
        diff = abs(calculated - truth)

        assert diff < 10e-12  # Less than 10 femptosecond difference


@pytest.mark.parametrize(
    "solver", [quartic.QuarticSolver.NUMERIC, quartic.QuarticSolver.HYBRID]
)
def test_no_ball_ball_collisions_for_intersecting_balls(solver: quartic.QuarticSolver):
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
    w = ptmath.cross(np.array([0, 0, 1]), v) / ball.params.R

    system.balls["cue"].state.rvw[1] = v
    system.balls["cue"].state.rvw[2] = w
    system.balls["cue"].state.s = const.rolling

    # The cue is truly rolling
    _assert_rolling(system.balls["cue"].state.rvw, system.balls["cue"].params.R)

    assert (
        get_next_event(system, quartic_solver=solver).event_type != EventType.BALL_BALL
    )
    assert (
        get_next_ball_ball_collision(system, CollisionCache(), solver=solver).time
        == np.inf
    )
