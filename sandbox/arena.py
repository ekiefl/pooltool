#! /usr/bin/env python
"""This illustrates how shots can be visualized multiple times in a single script"""

import numpy as np

import pooltool as pt

run = pt.terminal.Run()

get_pos = lambda table, ball: (
    (table.w - 2 * ball.R) * np.random.rand() + ball.R,
    (table.l - 2 * ball.R) * np.random.rand() + ball.R,
    ball.R,
)


def place_ball(i, balls, table):
    ball = pt.Ball(i)
    while True:
        new_pos = get_pos(table, ball)
        ball.rvw[0] = new_pos

        for other in balls.values():
            if pt.physics.is_overlapping(ball.rvw, other.rvw, ball.R, other.R):
                break
        else:
            return ball


def main(args):
    if not args.no_viz:
        interface = pt.ShotViewer()
    while True:
        # setup table, cue, and cue ball
        table = pt.Table.from_table_specs(pt.PocketTableSpecs(l=4, w=2))

        balls = {}
        balls["cue"] = place_ball("cue", balls, table)
        for i in range(args.N):
            balls[str(i)] = place_ball(str(i), balls, table)

        cue = pt.Cue(cueing_ball=balls["cue"])

        # Aim at the head ball then strike the cue ball
        cue.aim_at_ball(balls["1"])
        cue.strike(V0=40)

        # Evolve the shot
        shot = pt.System(cue=cue, table=table, balls=balls)
        try:
            shot.simulate(continuize=False, quiet=False)
        except KeyboardInterrupt:
            shot.progress.end()
            break
        except:
            shot.progress.end()
            shot.run.info("Shot calculation failed", ":(")
            continue

        if not args.no_viz:
            interface.show(shot)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser("A large arena with many balls")
    ap.add_argument("-N", type=int, default=50, help="The number of balls")
    ap.add_argument(
        "--no-viz", action="store_true", help="If set, the break will not be visualized"
    )
    args = ap.parse_args()
    main(args)
