#! /usr/bin/env python
"""This is a basic example of the pooltool API"""

import sys
from pathlib import Path

import numpy as np

import pooltool as pt
from pooltool.utils import PProfile


def main(args):
    if not args.no_viz and not args.profile_it:
        interface = pt.ShotViewer()

    if args.seed:
        np.random.seed(args.seed)

    if args.load:
        shot = pt.System.load(args.load)
    else:
        shot = pt.System(
            cue=pt.Cue(cue_ball_id="cue"),
            table=(table := pt.Table.default()),
            balls=pt.get_nine_ball_rack(table, spacing_factor=args.spacing_factor),
        )

        # Aim at the head ball
        shot.strike(V0=args.V0, phi=pt.aim.at_ball(shot, "1"))

    # Time the shot
    if args.time_it:
        N = 20
        simulate_times = np.zeros(N)
        continuize_times = np.zeros(N)

        # Burn a run (numba cache loading)
        pt.simulate(shot, continuous=True)

        for i in range(N):
            # In what follows, copy beforehand and use inplace=True to avoid timing the
            # copy operation

            copy = shot.copy()

            with pt.terminal.TimeCode(quiet=True) as timer:
                pt.simulate(copy, inplace=True)
            simulate_times[i] = timer.time.total_seconds()

            with pt.terminal.TimeCode(quiet=True) as timer:
                pt.continuize(copy, inplace=True)
            continuize_times[i] = timer.time.total_seconds()

        run = pt.terminal.Run()

        mu = np.mean(simulate_times)
        stdev = np.std(simulate_times)
        run.info_single(
            f"Shot evolution algorithm: ({mu:.3f} +- {stdev:.3f}) ({N} trials)"
        )

        mu = np.mean(continuize_times)
        stdev = np.std(continuize_times)
        run.info_single(f"Continuize: ({mu:.3f} +- {stdev:.3f}) ({N} trials)")

    # Time the shot
    if args.profile_it:
        # Burn a run (numba cache loading)
        copy = shot.copy()
        pt.simulate(copy, inplace=True)

        run = pt.terminal.Run()
        run.info_single("Profiling `simulate` and `continuize` (may take awhile)")

        with PProfile(Path("cachegrind.out.simulate")):
            pt.simulate(shot, inplace=True)
        with PProfile(Path("cachegrind.out.continuize")):
            pt.continuize(shot, inplace=True)

        sys.exit()

    # Evolve the shot
    pt.simulate(shot, inplace=True)

    if not args.no_viz:
        interface.show(shot)

    if args.save:
        shot.save(args.save)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser("A good old 9-ball break")
    ap.add_argument(
        "--no-viz", action="store_true", help="If set, the break will not be visualized"
    )
    ap.add_argument(
        "--spacing-factor",
        type=float,
        default=1e-3,
        help="What fraction of the ball radius should each ball be randomly separated by in the rack?",
    )
    ap.add_argument(
        "--V0",
        type=float,
        default=8,
        help="With what speed should the cue stick strike the cue ball?",
    )
    ap.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Provide a random seed if you want reproducible results",
    )
    ap.add_argument(
        "--save", type=str, default=None, help="Filepath that shot will be saved to"
    )
    ap.add_argument(
        "--load",
        type=str,
        default=None,
        help="Don't create a new break, just simulate this system",
    )
    ap.add_argument(
        "--time-it",
        action="store_true",
        help="Simulate multiple times, calculating the average calculation time (w/o continuize)",
    )
    ap.add_argument(
        "--profile-it",
        action="store_true",
        help="Profile and spit out a cachegrind file (cachegrind.out.simulate and cachegrind.out.continuize)",
    )

    args = ap.parse_args()

    main(args)
