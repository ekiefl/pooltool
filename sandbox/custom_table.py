#! /usr/bin/env python
"""This examples how to make a custom pool table and ball parameters"""

from typing import Optional

import numpy as np

import pooltool as pt
from pooltool.ptmath import norm3d


def custom_ball_params() -> pt.BallParams:
    return pt.BallParams(
        m=0.170097,
        R=0.028575,
        u_s=0.2,
        u_r=0.01,
        u_sp_proportionality=10 * 2 / 5 / 9,
        e_c=0.85,
        f_c=0.2,
        g=9.81,
    )


def custom_table_specs() -> pt.objects.PocketTableSpecs:
    return pt.objects.PocketTableSpecs(
        l=1.9812,
        w=1.9812 / 2,
        cushion_width=2 * 2.54 / 100,
        cushion_height=0.64 * 2 * 0.028575,
        corner_pocket_width=0.10,
        corner_pocket_angle=1,
        corner_pocket_depth=0.0398,
        corner_pocket_radius=0.124 / 2,
        corner_jaw_radius=0.08,
        side_pocket_width=0.08,
        side_pocket_angle=3,
        side_pocket_depth=0.00437,
        side_pocket_radius=0.129 / 2,
        side_jaw_radius=0.03,
    )


def closest_ball(system: pt.System) -> str:
    """Return ball ID closest to the cue ball"""
    cueball = system.balls["cue"]

    closest_id: Optional[str] = None
    closest_dist = np.inf

    for ball in system.balls.values():
        if ball.id == "cue":
            continue

        if (dist := norm3d(cueball.xyz - ball.xyz)) < closest_dist:
            closest_dist = dist
            closest_id = ball.id

    assert closest_id is not None
    return closest_id


def main():
    # Ball parameters and table specifications
    ball_params = custom_ball_params()
    table_specs = custom_table_specs()

    # Build a table from the table specs
    table = pt.Table.from_table_specs(table_specs)

    # Now build the ball layout from the ball parameters and table
    balls = pt.get_rack(pt.GameType.EIGHTBALL, table=table, ball_params=ball_params)

    # Build a cue stick
    cue = pt.Cue.default()

    # Compile everythig into a system
    system = pt.System(
        cue=cue,
        table=table,
        balls=balls,
    )

    # Put some energy into the system
    system.cue.set_state(
        V0=7,
        phi=pt.aim.at_ball(system, closest_ball(system), cut=-25),
    )

    # Now simulate it
    pt.simulate(system, inplace=True)

    # Now visualize it
    pt.show(system)


if __name__ == "__main__":
    main()
