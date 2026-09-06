#! /usr/bin/env python
"""This sets up a 9-ball break forever and ever"""

import pooltool as pt


def main(args):
    count = 0
    while True:
        shot = pt.System(
            cue=pt.Cue(cue_ball_id="cue"),
            table=(table := pt.Table.default(table_type=pt.TableType.POCKET)),
            balls=pt.get_rack(
                pt.GameType.NINEBALL, table, spacing_factor=args.spacing_factor
            ),
        )

        # Aim at the head ball then strike the cue ball
        shot.strike(V0=args.V0, phi=pt.aim.at_ball(shot, "1", cut=0))

        # Evolve the shot
        pt.simulate(shot, inplace=True)

        count += 1
        print(count)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser("A good old 9-ball break")
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

    args = ap.parse_args()

    main(args)
