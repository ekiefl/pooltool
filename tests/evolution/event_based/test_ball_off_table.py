import attrs
import numpy as np
import pytest

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.events import EventType, filter_type
from pooltool.evolution.engine import SimulationEngine
from pooltool.evolution.event_based._utils import _system_has_energy
from pooltool.evolution.event_based.cache import CollisionCache
from pooltool.evolution.event_based.detect.ball_ball import get_next_ball_ball_event
from pooltool.evolution.event_based.detect.ball_off_table import (
    ball_off_table_time,
    get_next_ball_off_table_event,
    off_table_bounds,
    pocket_circles,
)
from pooltool.evolution.event_based.simulate import simulate
from pooltool.game.datatypes import GameType
from pooltool.layouts import get_rack
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.cue.datatypes import Cue
from pooltool.objects.table.components import Pocket
from pooltool.objects.table.datatypes import Table
from pooltool.objects.table.specs import TableType
from pooltool.physics.evolve import evolve_ball_motion
from pooltool.physics.resolve import Resolver
from pooltool.system.datatypes import System


def _launch(ball: Ball, xy: tuple[float, float], height: float, v: tuple[float, float, float]) -> None:
    ball.state.rvw[0] = [xy[0], xy[1], ball.params.R + height]
    ball.state.rvw[1] = v
    ball.state.s = const.airborne


@pytest.fixture
def system() -> System:
    return System.example()


@pytest.fixture
def engine_3d() -> SimulationEngine:
    return SimulationEngine(is_3d=True, resolver=Resolver.default(is_3d=True))


def test_no_airborne_balls_returns_inf_time(system: System):
    event = get_next_ball_off_table_event(system, CollisionCache())
    assert event.event_type == EventType.BALL_OFF_TABLE
    assert event.time == np.inf


def test_airborne_ball_without_horizontal_velocity_returns_inf(system: System):
    ball = next(iter(system.balls.values()))
    _launch(ball, system.table.center, 0.1, (0.0, 0.0, 1.0))

    event = get_next_ball_off_table_event(system, CollisionCache())
    assert event.time == np.inf


def test_airborne_ball_returns_boundary_crossing_time(system: System):
    ball = next(iter(system.balls.values()))
    _launch(ball, (0.1, system.table.l / 4), 0.1, (-2.0, 0.0, 0.0))

    event = get_next_ball_off_table_event(system, CollisionCache())

    x_min, _, _, _ = off_table_bounds(system.table)
    assert event.ids[0] == ball.id
    assert event.time == pytest.approx((0.1 - x_min) / 2.0)


def test_returns_soonest_ball(system: System):
    balls = list(system.balls.values())
    near, far = balls[0], balls[1]
    _launch(near, (0.1, system.table.l / 4), 0.1, (-2.0, 0.0, 0.0))
    _launch(far, (0.5, system.table.l / 4), 0.1, (-2.0, 0.0, 0.0))

    event = get_next_ball_off_table_event(system, CollisionCache())
    assert event.ids[0] == near.id


def _side_pocket_flight(table: Table, v: tuple[float, float, float]) -> Ball:
    """An airborne ball heading straight for the left side pocket's mouth."""
    ball = Ball.create("cue")
    _launch(ball, (0.2, table.l / 2), 0.05, v)
    return ball


def _disk_exit_time(ball: Ball, a: float, b: float, r: float) -> float:
    x, y, _ = ball.state.rvw[0]
    vx, vy, _ = ball.state.rvw[1]
    px, py = x - a, y - b
    A = vx * vx + vy * vy
    B = 2.0 * (px * vx + py * vy)
    C = px * px + py * py - r * r
    return (-B + np.sqrt(B * B - 4.0 * A * C)) / (2.0 * A)


def test_path_through_pocket_defers_to_circle_exit():
    """Crossing the edge on the way into a pocket is not leaving the table."""
    table = Table.default()
    ball = _side_pocket_flight(table, (-3.0, 0.0, 1.5))
    pocket = table.pockets["lc"]

    t = ball_off_table_time(
        ball.state.rvw,
        ball.state.s,
        *off_table_bounds(table),
        *pocket_circles(table),
        ball.params.R,
        ball.params.g,
    )

    assert t == pytest.approx(_disk_exit_time(ball, pocket.a, pocket.b, pocket.radius))
    assert t > 0.2 / 3.0

    rvw, s = evolve_ball_motion(
        ball.state.s,
        ball.state.rvw,
        ball.params.R,
        ball.params.m,
        ball.params.u_s,
        ball.params.u_sp,
        ball.params.u_r,
        ball.params.g,
        t,
    )
    x, y, z = rvw[0]

    assert s == const.airborne
    assert z > ball.params.R
    assert np.hypot(x - pocket.a, y - pocket.b) == pytest.approx(pocket.radius)
    assert x < pocket.a


_POCKET_RADIUS = 0.062


@pytest.fixture
def billiard() -> Table:
    """A billiard table: no pockets, so each test adds only the pocket it is about."""
    return Table.default(TableType.BILLIARD)


def _add_pocket(table: Table, pocket_id: str, xy: tuple[float, float]) -> Table:
    pocket = Pocket(id=pocket_id, center=np.array([*xy, 0.0]), radius=_POCKET_RADIUS)
    return attrs.evolve(table, pockets={**table.pockets, pocket_id: pocket})


def _edge_ball(table: Table) -> Ball:
    """An airborne ball at the table's center flying toward the low-x edge."""
    ball = Ball.create("cue")
    _launch(ball, table.center, 0.3, (-2.0, 0.0, 0.0))
    return ball


def _time(ball: Ball, table: Table) -> float:
    return ball_off_table_time(
        ball.state.rvw,
        ball.state.s,
        *off_table_bounds(table),
        *pocket_circles(table),
        ball.params.R,
        ball.params.g,
    )


def test_interior_pocket_on_the_track_does_not_open_the_boundary(billiard: Table):
    """A pocket inside the playing surface is passed before the edge is reached."""
    ball = _edge_ball(billiard)
    cx, cy = billiard.center
    table = _add_pocket(billiard, "mid", (cx / 2, cy))

    assert _time(ball, table) == pytest.approx(_time(ball, billiard))
    assert _time(ball, table) == pytest.approx(cx / 2.0)


def test_interior_pocket_around_the_ball_does_not_open_the_boundary(billiard: Table):
    ball = _edge_ball(billiard)
    table = _add_pocket(billiard, "mid", billiard.center)

    assert _time(ball, table) == pytest.approx(_time(ball, billiard))


def test_exterior_pocket_off_the_track_does_not_open_the_boundary(billiard: Table):
    """A pocket beyond the edge but away from the track has no effect."""
    ball = _edge_ball(billiard)
    _, cy = billiard.center
    table = _add_pocket(billiard, "side", (-0.2, cy + 0.5))

    assert _time(ball, table) == pytest.approx(_time(ball, billiard))


def test_path_missing_every_pocket_leaves_at_the_edge():
    table = Table.default()
    ball = Ball.create("cue")
    _launch(ball, (0.1, table.l / 4), 0.1, (-2.0, 0.0, 0.0))

    t = ball_off_table_time(
        ball.state.rvw,
        ball.state.s,
        *off_table_bounds(table),
        *pocket_circles(table),
        ball.params.R,
        ball.params.g,
    )

    assert t == pytest.approx(0.1 / 2.0)


def test_flight_into_side_pocket_is_pocketed(engine_3d: SimulationEngine):
    """Regression: the ball used to freeze at the edge before it could be pocketed."""
    table = Table.default()
    ball = _side_pocket_flight(table, (-2.0, 0.0, 0.3))

    shot = System(cue=Cue(cue_ball_id="cue"), table=table, balls=(ball,))
    simulate(shot, engine=engine_3d, inplace=True)

    assert len(filter_type(shot.events, EventType.BALL_POCKET)) == 1
    assert len(filter_type(shot.events, EventType.BALL_OFF_TABLE)) == 0
    assert shot.balls["cue"].state.s == const.pocketed


def test_flight_over_side_pocket_leaves_at_its_far_side(engine_3d: SimulationEngine):
    """A ball clearing the pocket leaves the table where it exits the pocket circle."""
    table = Table.default()
    ball = _side_pocket_flight(table, (-3.0, 0.0, 1.5))
    pocket = table.pockets["lc"]
    t_exit = _disk_exit_time(ball, pocket.a, pocket.b, pocket.radius)

    shot = System(cue=Cue(cue_ball_id="cue"), table=table, balls=(ball,))
    simulate(shot, engine=engine_3d, inplace=True)

    off = filter_type(shot.events, EventType.BALL_OFF_TABLE)
    assert len(off) == 1
    assert off[0].time == pytest.approx(t_exit)
    assert len(filter_type(shot.events, EventType.BALL_POCKET)) == 0
    assert shot.balls["cue"].state.s == const.off_table
    assert shot.balls["cue"].state.rvw[0, 0] == pytest.approx(pocket.a - pocket.radius)


def test_ball_flying_over_cushion_goes_off_table(engine_3d: SimulationEngine):
    """A ball clearing the cushion crosses the boundary, freezes there, and the shot ends."""
    table = Table.default()
    ball = Ball.create("cue")
    _launch(ball, (0.1, table.l / 4), 0.2, (-2.0, 0.0, 1.0))

    shot = System(cue=Cue(cue_ball_id="cue"), table=table, balls=(ball,))
    simulate(shot, engine=engine_3d, inplace=True)

    assert len(filter_type(shot.events, EventType.BALL_OFF_TABLE)) == 1
    assert len(filter_type(shot.events, EventType.BALL_LINEAR_CUSHION)) == 0

    state = shot.balls["cue"].state
    x_min, _, _, _ = off_table_bounds(table)
    assert state.s == const.off_table
    assert np.isfinite(state.rvw).all()
    assert state.rvw[0, 0] == pytest.approx(x_min)
    assert state.rvw[1] == pytest.approx([0.0, 0.0, 0.0])
    assert state.rvw[2] == pytest.approx([0.0, 0.0, 0.0])
    assert shot.events[-1].time < 1.0


def test_low_hop_hits_cushion_instead(engine_3d: SimulationEngine):
    """A ball too low to clear the cushion collides with it and stays on the table."""
    table = Table.default()
    ball = Ball.create("cue")
    _launch(ball, (0.1, table.l / 4), 0.002, (-2.0, 0.0, 0.0))

    shot = System(cue=Cue(cue_ball_id="cue"), table=table, balls=(ball,))
    simulate(shot, engine=engine_3d, inplace=True)

    assert len(filter_type(shot.events, EventType.BALL_LINEAR_CUSHION)) >= 1
    assert len(filter_type(shot.events, EventType.BALL_OFF_TABLE)) == 0
    assert shot.balls["cue"].state.s in const.on_table


@pytest.fixture
def rack_with_ball_off_table() -> System:
    """A nine-ball rack whose 3 ball sits frozen off the table at rail height."""
    table = Table.default()
    shot = System(
        cue=Cue(cue_ball_id="cue"),
        table=table,
        balls=get_rack(GameType.NINEBALL, table),
    )
    gone = shot.balls["3"]
    gone.state.rvw[0] = [-0.03, table.l / 4, gone.params.R + 0.1]
    gone.state.s = const.off_table
    return shot


def test_frozen_off_table_ball_carries_no_energy(rack_with_ball_off_table: System):
    """Regression: its height above the cloth used to count as potential energy."""
    assert not _system_has_energy(rack_with_ball_off_table)


def test_shot_proceeds_with_a_ball_off_table(
    rack_with_ball_off_table: System, engine_3d: SimulationEngine
):
    """Regression: the phantom energy suppressed the cue strike, so no shot happened."""
    shot = rack_with_ball_off_table
    shot.strike(V0=2.0, phi=90.0)
    simulate(shot, engine=engine_3d, inplace=True)

    assert len(filter_type(shot.events, EventType.STICK_BALL)) == 1
    assert shot.balls["3"].state.s == const.off_table


def test_off_table_ball_takes_part_in_no_collisions(engine_3d: SimulationEngine):
    """A ball flying through a frozen off-table ball is not deflected by it.

    Balls leaving along the same trajectory pile up at the same boundary point, so the
    later ball's path runs straight through the earlier one. Out-of-play balls take
    part in no physics, so no collision may be detected and the frozen ball must stay
    exactly as it was.
    """
    table = Table.default()
    frozen = Ball.create("frozen")
    x_min, _, _, _ = off_table_bounds(table)
    frozen.state.rvw[0] = [x_min, table.l / 4, frozen.params.R + 0.1]
    frozen.state.s = const.off_table
    frozen_rvw = frozen.state.rvw.copy()

    flying = Ball.create("flying")
    _launch(flying, (0.3, table.l / 4), 0.1, (-2.0, 0.0, 0.8))

    shot = System(cue=Cue(cue_ball_id="flying"), table=table, balls=(frozen, flying))
    simulate(shot, engine=engine_3d, inplace=True)

    assert len(filter_type(shot.events, EventType.BALL_BALL)) == 0
    assert len(filter_type(shot.events, EventType.BALL_OFF_TABLE)) == 1
    assert shot.balls["frozen"].state.s == const.off_table
    assert shot.balls["frozen"].state.rvw == pytest.approx(frozen_rvw)
    assert shot.balls["flying"].state.s == const.off_table

    assert ptmath.is_overlapping(
        shot.balls["flying"].state.rvw,
        shot.balls["frozen"].state.rvw,
        flying.params.R,
        frozen.params.R,
    )


def test_ball_intersecting_a_frozen_ball_is_not_colliding():
    """The ball-ball detector ignores a frozen ball even when another overlaps it.

    Overlapping balls are otherwise reported as colliding immediately, so this is the
    guard the flight through a frozen ball relies on.
    """
    table = Table.default()
    frozen = Ball.create("frozen")
    frozen.state.rvw[0] = [-0.03, table.l / 4, frozen.params.R + 0.1]
    frozen.state.s = const.off_table

    flying = Ball.create("flying")
    _launch(flying, (-0.03 + frozen.params.R, table.l / 4), 0.1, (-2.0, 0.0, 0.8))

    shot = System(cue=Cue(cue_ball_id="flying"), table=table, balls=(frozen, flying))

    event = get_next_ball_ball_event(shot, CollisionCache(), is_3d=True)

    assert event.time == np.inf
