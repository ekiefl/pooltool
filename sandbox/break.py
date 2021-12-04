#! /usr/bin/env python
"""This is a basic example of the pooltool API"""

import pooltool as pt

def main(args):
    if not args.no_viz:
        interface = pt.ShotViewer()

    if args.seed:
        import numpy as np
        np.random.seed(args.seed)

    table = pt.PocketTable(model_name='7_foot')
    balls = pt.get_nine_ball_rack(table, ordered=True)
    cue = pt.Cue(cueing_ball=balls['cue'])

    # Aim at the head ball then strike the cue ball
    cue.aim_at_ball(balls['1'])
    cue.strike(V0=8)

    # Evolve the shot
    shot = pt.System(cue=cue, table=table, balls=balls)
    shot.simulate(continuize=True)

    if not args.no_viz:
        interface.show(shot)


if __name__ == '__main__':
    import argparse

    ap = argparse.ArgumentParser('A good old 9-ball break')
    ap.add_argument('--no-viz', action='store_true', help="If set, the break will not be visualized")
    ap.add_argument('--seed', type=int, default=None, help="Provide a random seed if you want reproducible results")

    args = ap.parse_args()
    main(args)
