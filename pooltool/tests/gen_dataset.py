#! /usr/bin/env python
"""This is a basic example of the pooltool API"""

import pooltool as pt

from pooltool.error import ConfigError

import sys

from pathlib import Path

def main(args):
    if not args.force:
        raise ConfigError("Many of the unit tests are generated automatically by parsing the output of this script. "
                          "That means the output serves as a ground truth. By running this script, you are deciding "
                          "that a new ground truth should be issued, which is clearly no joke. Provide the flag --force "
                          "to proceed. The trajectories of the balls in this simmulation will be taken as true.")

    table = pt.PocketTable(model_name='7_foot')
    balls = pt.get_nine_ball_rack(table, ordered=True)
    cue = pt.Cue(cueing_ball=balls['cue'])

    # Aim at the head ball then strike the cue ball
    cue.aim_at_ball(balls['1'])
    cue.strike(V0=8)

    # Evolve the shot
    shot = pt.System(cue=cue, table=table, balls=balls)
    shot.simulate(continuize=False)

    # Visualize the shot
    interface = pt.ShotViewer()
    interface.show(shot, 'This is the new benchmark (continuize = False).')

    # Save the shot
    output_dir = Path(pt.__file__).parent / 'tests' / 'data'
    output_dir.mkdir(exist_ok=True)
    shot.save(output_dir / 'benchmark.pkl')


if __name__ == '__main__':
    import argparse

    description = "This script generates the file benchmark.pkl, a ground-truth file parsed by the unit tests"
    ap = argparse.ArgumentParser(description)

    ap.add_argument(
        '--force',
        action = 'store_true',
        help = 'Use to regenerate benchmark.pkl'
    )

    args = ap.parse_args()
    try:
        main(args)
    except ConfigError as e:
        print(e)
        sys.exit(1)


