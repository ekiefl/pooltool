#! /usr/bin/env python

import sys

import pooltool as pt
from pooltool.ani.globals import Global
from pooltool.ani.modes import ModeManager, all_modes


def main(args):
    shot = pt.System.load(args.path)

    # Burn a simulation to pre-load numba caches
    copy = shot.copy()
    pt.simulate(copy, inplace=True)
    pt.continuize(copy, inplace=True)

    shot = shot.copy()

    with pt.terminal.TimeCode(success_msg="Trajectories simulated in: "):
        pt.simulate(shot, inplace=True)

    with pt.terminal.TimeCode(success_msg="Trajectories continuized in: "):
        pt.continuize(shot, inplace=True)

    class TimedModeManager(ModeManager):
        def change_mode(self, *args, **kwargs):
            with pt.terminal.TimeCode(success_msg="Animation sequence rendered in: "):
                super().change_mode(*args, **kwargs)
            sys.exit()

    interface = pt.ShotViewer()
    Global.register_mode_mgr(TimedModeManager(all_modes))
    Global.mode_mgr.init_modes()
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
