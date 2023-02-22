#! /usr/bin/env python

import pooltool as pt

raise NotImplementedError("Needs a fixing after shot serialization is refactored")


def main(args):
    shot = pt.System(path=args.path)

    shot.simulate(quiet=True)
    shot.reset_balls()

    with pt.terminal.TimeCode(success_msg="Trajectories simulated in: "):
        shot.simulate(quiet=True)

    with pt.terminal.TimeCode(success_msg="Trajectories continuized in: "):
        shot.continuize(dt=1 / 60 * 2)

    class Interface(pt.ShotViewer):
        def __init__(self, *args, **kwargs):
            pt.ShotViewer.__init__(self, *args, **kwargs)

        def change_mode(self, *args, **kwargs):
            with pt.terminal.TimeCode(success_msg="Animation sequence rendered in: "):
                super().change_mode(*args, **kwargs)

    interface = Interface()
    interface.show(shot)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        "Compare timings of shot calculation, continuization, and animation rendering"
    )
    ap.add_argument(
        "--path",
        type=str,
        required=True,
        help="Filepath to a shot (you could generate this with sandbox/break.py, for example)",
    )

    args = ap.parse_args()

    main(args)
