import numpy as np
import pytest
from _helpers import build_3d_engine

import pooltool.constants as const
from pooltool.events import EventType, filter_type
from pooltool.evolution.event_based.cache import CollisionCache
from pooltool.evolution.event_based.detect.ball_pocket import (
    ball_pocket_collision_time_if_airborne,
    get_next_ball_pocket_event,
)
from pooltool.evolution.event_based.simulate import simulate
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.cue.datatypes import Cue
from pooltool.objects.table.datatypes import Table
from pooltool.objects.table.specs import TableType
from pooltool.physics.utils import get_airborne_time
from pooltool.system.datatypes import System

R_DEFAULT = 0.028575
G_DEFAULT = 9.81


def _airborne_rvw(
    x: float, y: float, z: float, vx: float = 0.0, vy: float = 0.0, vz: float = 0.0
) -> np.ndarray:
    return np.array(
        [[x, y, z], [vx, vy, vz], [0.0, 0.0, 0.0]],
        dtype=np.float64,
    )


def test_vertical_drop_into_pocket_center():
    """Strategy 1: ball with no xy velocity drops straight into the pocket."""
    a, b, r = 0.5, 0.5, 0.05
    rvw = _airborne_rvw(0.5, 0.5, R_DEFAULT + 0.1)

    t = ball_pocket_collision_time_if_airborne(rvw, a, b, r, G_DEFAULT, R_DEFAULT)

    airborne_time = get_airborne_time(rvw, R_DEFAULT, G_DEFAULT)
    assert t == pytest.approx(airborne_time - const.EPS)


def test_fast_low_traverse_returns_cylinder_midpoint():
    """Strategy 2: ball skims through the cylinder fast and low enough to ricochet.

    With ``z0 = 1.2 R`` (between ``R`` and ``7/5 R``) and high horizontal velocity,
    the influx and outflux heights both stay inside the ricochet window, so the
    function returns the average of the crossing times.
    """
    a, b, r = 0.0, 0.0, 0.05
    rvw = _airborne_rvw(-1.0, 0.0, 1.2 * R_DEFAULT, vx=100.0)

    t = ball_pocket_collision_time_if_airborne(rvw, a, b, r, G_DEFAULT, R_DEFAULT)

    # Trajectory crosses cylinder at t=0.0095 (influx) and t=0.0105 (outflux).
    assert t == pytest.approx(0.01, abs=1e-6)


def test_fly_over_returns_inf():
    """Both influx and outflux above 7/5*R → ball flies over the pocket."""
    a, b, r = 0.0, 0.0, 0.05
    rvw = _airborne_rvw(-1.0, 0.0, 0.5, vx=1.0)

    t = ball_pocket_collision_time_if_airborne(rvw, a, b, r, G_DEFAULT, R_DEFAULT)

    assert t == np.inf


def test_airborne_ball_above_pocket_is_pocketed():
    """End-to-end: an airborne ball dropping into a pocket produces a BALL_POCKET event."""
    table = Table.default()
    pocket = next(iter(table.pockets.values()))

    ball = Ball.create("cue")
    ball.state.rvw[0, 0] = pocket.a
    ball.state.rvw[0, 1] = pocket.b
    ball.state.rvw[0, 2] = ball.params.R + 0.1
    ball.state.s = const.airborne

    shot = System(cue=Cue(), table=table, balls=(ball,))
    simulate(shot, engine=build_3d_engine(), inplace=True)

    pocket_events = filter_type(shot.events, EventType.BALL_POCKET)
    assert len(pocket_events) == 1
    assert shot.balls["cue"].state.s == const.pocketed


def test_detector_skips_when_no_pockets():
    """A table without pockets short-circuits to an inf-time null event."""
    table = Table.default(TableType.BILLIARD)

    ball = Ball.create("cue")
    ball.state.rvw[0, 2] = ball.params.R + 0.1
    ball.state.s = const.airborne

    shot = System(cue=Cue(cue_ball_id="cue"), table=table, balls=(ball,))

    event = get_next_ball_pocket_event(shot, CollisionCache())
    assert event.time == np.inf
