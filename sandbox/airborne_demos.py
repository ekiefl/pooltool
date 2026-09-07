#! /usr/bin/env python
"""Demos 3D trajectory (work in progress)

Usage:
    python sandbox/airborne_demos.py --name drop
"""

import argparse

import attrs
import numpy as np

from pooltool import constants as const
from pooltool.evolution.engine import SimulationEngine
from pooltool.evolution.event_based.simulate import simulate
from pooltool.interact import show
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.ball.sets import BallSet
from pooltool.objects.cue.datatypes import Cue
from pooltool.objects.table.datatypes import Table
from pooltool.physics.dimensionality import Dim
from pooltool.physics.resolve.ball_ball.frictional_inelastic import (
    FrictionalInelastic3D,
)
from pooltool.physics.resolve.ball_cushion.stronge_compliant import (
    StrongeCompliantCircular3D,
    StrongeCompliantLinear3D,
)
from pooltool.physics.resolve.resolver import Resolver
from pooltool.physics.resolve.stick_ball.instantaneous_point import (
    InstantaneousPoint3D,
)
from pooltool.system.datatypes import System


def _build_3d_engine() -> SimulationEngine:
    """Build a SimulationEngine with ``is_3d=True``.

    Every resolver strategy that carries a ``dim`` tag is patched to
    ``Dim.BOTH`` so the engine constructs; the stick-ball strategy is
    swapped to ``InstantaneousPoint3D`` so cue elevation produces real
    vertical velocity, the ball-ball strategy to ``FrictionalInelastic3D`` so
    collisions keep their vertical velocity component, and the cushion strategies to
    the Stronge 3D models so airborne balls rebound off the nose in 3D.
    """
    # Patches all defaults to dim.BOTH so the engine constructs
    resolver = Resolver.default()
    for field in attrs.fields(type(resolver)):
        strategy = getattr(resolver, field.name)
        if hasattr(strategy, "dim"):
            strategy.dim = Dim.BOTH

    # Replace all working 3D resolvers
    resolver.stick_ball = InstantaneousPoint3D()
    resolver.ball_ball = FrictionalInelastic3D()
    resolver.ball_linear_cushion = StrongeCompliantLinear3D()
    resolver.ball_circular_cushion = StrongeCompliantCircular3D()

    return SimulationEngine(resolver=resolver, is_3d=True)


def drop() -> System:
    """Ball dropped from 0.3 m with a small horizontal nudge in +x."""
    ball = Ball.create("cue", xy=(0.5, 0.5))
    ball.state.rvw[0, 2] = 0.3
    ball.state.rvw[1, 0] = 0.5
    ball.state.s = const.airborne

    return System(
        cue=Cue(cue_ball_id="cue"),
        table=Table.default(),
        balls=(ball,),
    )


def impulse_into() -> System:
    """Strong downward strike with a small horizontal nudge in +y."""
    ball = Ball.create("cue", xy=(0.5, 0.5))
    ball.state.rvw[1, 1] = 0.5
    ball.state.rvw[1, 2] = -5.0
    ball.state.s = const.airborne

    return System(
        cue=Cue(cue_ball_id="cue"),
        table=Table.default(),
        balls=(ball,),
    )


def jump() -> System:
    """A genuine jump shot — cue strike at 60° elevation produces vz via the 3D resolver.

    No handcrafted ``rvw`` here: the cue strikes a ball at rest on the table
    surface, and ``InstantaneousPoint3D`` lifts it off via ``v·sin(theta)``.
    """
    ball = Ball.create("cue", xy=(0.5, 0.5))
    cue = Cue(cue_ball_id="cue")
    cue.set_state(V0=2.0, phi=90.0, theta=60.0, a=0.0, b=0.0)

    return System(
        cue=cue,
        table=Table.default(),
        balls=(ball,),
    )


def drop_onto_ball() -> System:
    """A ball at rest directly beneath a second ball dropped from 0.25 m above it."""
    bottom = Ball.create("1", xy=(0.5, 0.5))

    top = Ball.create("cue", xy=(0.52, 0.5))
    top.state.rvw[0, 2] = 3 * top.params.R + 0.5
    top.state.s = const.airborne

    return System(
        cue=Cue(cue_ball_id="cue"),
        table=Table.default(),
        balls=(bottom, top),
    )


def drop_together() -> System:
    """Two touching balls dropped together from rest, the top one offset 2 cm sideways.

    The pair falls as a unit until the bottom ball meets the table. The tilted line of
    centers then sends the top ball off to the side. Exhibits an exected event order.
    """
    offset = 0.01
    drop_height = 0.3

    bottom1 = Ball.create("1", xy=(0.5, 0.5))
    bottom1.state.rvw[0, 2] = bottom1.params.R + drop_height
    bottom1.state.s = const.airborne

    R = bottom1.params.R
    top1 = Ball.create("cue", xy=(0.5 + offset, 0.5))
    top1.state.rvw[0, 2] = (
        bottom1.state.rvw[0, 2] + np.sqrt((2 * R) ** 2 - offset**2) + 0.1
    )
    top1.state.s = const.airborne

    bottom2 = Ball.create("3", xy=(0.5, 0.7))
    bottom2.state.rvw[0, 2] = bottom2.params.R + drop_height
    bottom2.state.s = const.airborne

    R = bottom2.params.R
    top2 = Ball.create("4", xy=(0.5 + offset, 0.7))
    top2.state.rvw[0, 2] = bottom2.state.rvw[0, 2] + np.sqrt((2 * R) ** 2 - offset**2)
    top2.state.s = const.airborne

    return System(
        cue=Cue(cue_ball_id="cue"),
        table=Table.default(),
        balls=(bottom1, top1, bottom2, top2),
    )


def airborne_pocket_collision() -> System:
    """Six airborne balls dropping toward a corner pocket from varied heights.

    Exercises both Strategy 1 (landing directly inside the pocket) and Strategy 2
    (xy trajectory crossing the pocket cylinder mid-fall) in
    :func:`pooltool.evolution.event_based.detect.ball_pocket.ball_pocket_collision_time_if_airborne`.
    """
    ball = Ball.create("cue")
    scale = 0.18
    ball.state.rvw = np.array(
        [
            [0.8, 0.2, 1.228575],
            [1.8 * scale, -1.8 * scale, 1.5],
            [0, 0, 0],
        ]
    )
    ball.state.s = const.airborne

    other = Ball.create("1")
    scale = 0.27
    other.state.rvw = np.array(
        [
            [0.8, 0.2, 1.0],
            [1.8 * scale, -1.8 * scale, 1.5],
            [0, 0, 0],
        ]
    )
    other.state.s = const.airborne

    another = Ball.create("2")
    scale = 0.11
    another.state.rvw = np.array(
        [
            [0.8, 0.2, 0.8],
            [1.8 * scale, -1.8 * scale, 1.5],
            [0, 0, 0],
        ]
    )
    another.state.s = const.airborne

    fast1 = Ball.create("3")
    scale = 2
    fast1.state.rvw = np.array(
        [
            [0.3, 0.7, fast1.params.R * 7 / 5],
            [1.8 * scale, -1.8 * scale, 0.6],
            [0, 0, 0],
        ]
    )
    fast1.state.s = const.airborne

    fast2 = Ball.create("4")
    scale = 2
    fast2.state.rvw = np.array(
        [
            [0.8, 0.2, fast2.params.R * 7 / 5],
            [1.8 * scale, -1.8 * scale, -2.0],
            [0, 0, 0],
        ]
    )
    fast2.state.s = const.airborne

    vertical = Ball.create("5")
    vertical.state.rvw = np.array(
        [
            [1.0, -0.05, 0.75],
            [0, 0, 0],
            [0, 0, 0],
        ]
    )
    vertical.state.s = const.airborne

    shot = System(
        cue=Cue(cue_ball_id="cue"),
        table=Table.default(),
        balls=(ball, other, another, fast1, fast2, vertical),
    )
    shot.set_ballset(BallSet("pooltool_pocket"))

    return shot


def cushion_lofts() -> System:
    """Sixteen balls at one x coordinate, all moving +x at the same speed with increasing +z velocity.

    The balls are spread along the table's length in two groups of eight, one per long
    cushion segment, leaving a gap at the side pockets. The cue ball stays on the table;
    the rest meet the cushion nose in the air at increasing heights.
    """
    table = Table.default()
    x = 0.75
    vx = 3.0
    ys = np.concatenate((np.linspace(0.15, 0.85, 8), np.linspace(1.13, 1.83, 8)))
    vzs = np.concatenate(([0.0], np.linspace(0.4, 0.85, 15)))
    ids = ["cue"] + [str(i) for i in range(1, 16)]

    balls = []
    for ball_id, y, vz in zip(ids, ys, vzs):
        ball = Ball.create(ball_id, xy=(x, y))
        ball.state.rvw[1] = [vx, 0.0, vz]
        if vz > 0:
            ball.state.s = const.airborne
        else:
            ball.state.s = const.sliding
        balls.append(ball)

    shot = System(cue=Cue(cue_ball_id="cue"), table=table, balls=balls)
    shot.set_ballset(BallSet("pooltool_pocket"))
    return shot


_map = {
    "drop": drop,
    "impulse_into": impulse_into,
    "jump": jump,
    "drop_onto_ball": drop_onto_ball,
    "drop_together": drop_together,
    "pocket_collision": airborne_pocket_collision,
    "cushion_lofts": cushion_lofts,
}


def main(name: str) -> None:
    engine = _build_3d_engine()
    shot = _map[name]()
    simulate(shot, engine=engine, inplace=True, max_events=5000)
    show(shot)


if __name__ == "__main__":
    ap = argparse.ArgumentParser("Airborne ball demos in 3D mode.")
    ap.add_argument("--name", choices=list(_map.keys()) + ["all"], required=True)
    args = ap.parse_args()

    if args.name == "all":
        for name in _map:
            print(f"Running {name}...")
            main(name)
    else:
        main(args.name)
