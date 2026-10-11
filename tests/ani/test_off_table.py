import numpy as np
import pytest

import pooltool.constants as const
from pooltool.ani import off_table
from pooltool.ani.off_table import FADE_START, TAIL_DURATION
from pooltool.ani.table_box import TableBox
from pooltool.evolution.continuous import continuize_ball
from pooltool.evolution.engine import SimulationEngine
from pooltool.evolution.event_based.simulate import simulate
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.cue.datatypes import Cue
from pooltool.objects.table.datatypes import Table
from pooltool.physics.resolve.resolver import default_resolver_3d
from pooltool.system.datatypes import System
from pooltool.system.render import SystemRender

DT = 0.01
RAIL = 0.15
TOP = 0.047
FLOOR = -0.708


def _box(table: Table) -> TableBox:
    return TableBox(
        table.w, table.l, -RAIL, table.w + RAIL, -RAIL, table.l + RAIL, TOP, FLOOR
    )


def _fly_off(x0: float, v: tuple[float, float, float], height: float) -> System:
    """A single ball launched over the left cushion, simulated."""
    table = Table.default()
    ball = Ball.create("cue")
    ball.state.rvw[0] = [x0, table.l / 4, ball.params.R + height]
    ball.state.rvw[1] = v
    ball.state.rvw[2] = [1.0, 2.0, 3.0]
    ball.state.s = const.airborne

    shot = System(cue=Cue(cue_ball_id="cue"), table=table, balls=(ball,))
    engine = SimulationEngine(is_3d=True, resolver=default_resolver_3d())
    simulate(shot, engine=engine, inplace=True)
    return shot


def _render_history(shot: System):
    ball = shot.balls["cue"]
    crossing = off_table.crossing_event(shot, "cue")
    assert crossing is not None
    history = off_table.with_tail(
        continuize_ball(ball, DT),
        off_table.exit_state(crossing),
        ball.params,
        _box(shot.table),
        DT,
    )
    tail_start = int(np.argmax(history.ts >= crossing.time))
    return history, tail_start


@pytest.fixture
def fast() -> System:
    """Clears the rail entirely and lands on the floor."""
    return _fly_off(0.1, (-2.0, 0.3, 1.0), 0.2)


@pytest.fixture
def slow() -> System:
    """Lands on the rail top and slides off its edge."""
    return _fly_off(0.05, (-0.5, 0.0, 1.2), 0.05)


def test_ball_that_stays_on_the_table_has_no_crossing_event():
    shot = simulate(System.example())
    assert off_table.crossing_event(shot, "cue") is None


def test_exit_state_is_the_airborne_state_at_the_crossing(fast: System):
    crossing = off_table.crossing_event(fast, "cue")
    assert crossing is not None

    exit = off_table.exit_state(crossing)
    frozen = fast.balls["cue"].history[-1]

    assert exit.t == crossing.time
    assert exit.s == const.airborne
    assert np.array_equal(exit.rvw[0], frozen.rvw[0])
    assert exit.rvw[1][0] < 0.0
    assert frozen.s == const.off_table
    assert not frozen.rvw[1].any()


def test_tail_replaces_the_frozen_states(fast: System):
    ball = fast.balls["cue"]
    continuized = continuize_ball(ball, DT)
    history, tail_start = _render_history(fast)

    assert const.off_table in continuized.ss
    assert const.off_table not in history.ss
    assert np.array_equal(history.rvws[:tail_start], continuized.rvws[:tail_start])
    assert np.array_equal(history.ts[:tail_start], continuized.ts[:tail_start])
    assert (np.diff(history.ts) > 0.0).all()


def test_tail_lasts_the_tail_duration_and_ends_halted(fast: System):
    crossing = off_table.crossing_event(fast, "cue")
    assert crossing is not None
    history, tail_start = _render_history(fast)

    assert history.ts[tail_start] == crossing.time
    assert history.ts[-1] == pytest.approx(crossing.time + TAIL_DURATION)
    assert np.diff(history.ts[tail_start:]) == pytest.approx(DT)
    assert history.ss[-1] == const.stationary
    assert not history.rvws[-1, 1].any()
    assert not history.rvws[-1, 2].any()
    assert FADE_START < TAIL_DURATION


@pytest.mark.parametrize("fixture", ["fast", "slow"])
def test_tail_moves_away_from_the_table_and_never_enters_it(fixture: str, request):
    shot = request.getfixturevalue(fixture)
    R = shot.balls["cue"].params.R
    box = _box(shot.table)
    history, tail_start = _render_history(shot)

    xs = history.rvws[tail_start:, 0, 0]
    assert (np.diff(xs) <= 0.0).all()

    for x, y, z in history.rvws[tail_start:, 0]:
        surface = box.top if box.contains(x, y) else box.floor
        assert z - R >= surface - 1e-9


def test_fast_ball_clears_the_rail_and_bounces_on_the_floor(fast: System):
    R = fast.balls["cue"].params.R
    history, tail_start = _render_history(fast)
    bottoms = history.rvws[tail_start:, 0, 2] - R

    assert bottoms.min() == pytest.approx(FLOOR)
    assert not _box(fast.table).contains(*history.rvws[-1, 0, :2])


def test_slow_ball_lands_on_the_rail_top_and_slides_off_it(slow: System):
    R = slow.balls["cue"].params.R
    box = _box(slow.table)
    history, tail_start = _render_history(slow)
    positions = history.rvws[tail_start:, 0]

    on_rail = [
        i
        for i, (x, y, z) in enumerate(positions)
        if box.contains(x, y) and z - R == pytest.approx(TOP)
    ]
    assert len(on_rail) > 1

    x, y, z = positions[-1]
    assert not box.contains(x, y)
    assert z - R < TOP


def test_resample_attaches_the_tail_and_the_crossing_time(fast: System):
    crossing = off_table.crossing_event(fast, "cue")
    assert crossing is not None

    render = SystemRender.from_system(fast)
    render.resample(DT)
    ball_render = render.balls["cue"]

    assert ball_render.left_table_at == crossing.time
    assert ball_render.history.ts[-1] == pytest.approx(crossing.time + TAIL_DURATION)
    assert len(ball_render.quats) == len(ball_render.history)
    assert len(ball_render.shadow_zs) == len(ball_render.history)
    assert const.off_table not in ball_render.history.ss


def test_resample_leaves_a_ball_on_the_table_alone():
    shot = simulate(System.example())
    render = SystemRender.from_system(shot)
    render.resample(DT)

    for ball_id, ball_render in render.balls.items():
        assert ball_render.left_table_at is None
        assert ball_render.history == continuize_ball(shot.balls[ball_id], DT)
