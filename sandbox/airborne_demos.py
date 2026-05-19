#! /usr/bin/env python
"""Demos 3D trajectory (work in progress)

Usage:
    python sandbox/airborne_demos.py --name drop
"""

import argparse

import attrs

from pooltool import constants as const
from pooltool.evolution.engine import SimulationEngine
from pooltool.evolution.event_based.simulate import simulate
from pooltool.interact import show
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.cue.datatypes import Cue
from pooltool.objects.table.datatypes import Table
from pooltool.physics.dimensionality import Dim
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
    vertical velocity.
    """
    # Patches all defaults to dim.BOTH so the engine constructs
    resolver = Resolver.default()
    for field in attrs.fields(type(resolver)):
        strategy = getattr(resolver, field.name)
        if hasattr(strategy, "dim"):
            strategy.dim = Dim.BOTH

    # Replace all working 3D resolvers
    resolver.stick_ball = InstantaneousPoint3D()

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


_map = {
    "drop": drop,
    "impulse_into": impulse_into,
    "jump": jump,
}


def main(name: str) -> None:
    engine = _build_3d_engine()
    shot = _map[name]()
    simulate(shot, engine=engine, inplace=True)
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
