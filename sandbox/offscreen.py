#! /usr/bin/env python
"""This illustrates how to render offscreen and save as images"""

import shutil
from pathlib import Path

import numpy as np

import pooltool as pt
from pooltool.ani.camera import camera_states


def main(args):
    interface = pt.ImageSaver()

    if args.seed:
        np.random.seed(args.seed)

    table = pt.Table.default()
    balls = pt.get_nine_ball_rack(
        table, ordered=True, spacing_factor=args.spacing_factor
    )
    cue = pt.Cue(cueing_ball=balls["cue"])

    # Aim at the head ball then strike the cue ball
    cue.aim_at_ball(balls["1"])
    cue.strike(V0=args.V0)

    # Evolve the shot
    shot = pt.System(cue=cue, table=table, balls=balls)
    shot = pt.simulate(shot)

    output = Path(__file__).parent / "offscreen_out"
    if output.exists():
        shutil.rmtree(output)
    output.mkdir()

    # These camera states can be found in pooltool/ani/camera/camera_states. You can
    # make your own by creating a new JSON in that directory. Reach out if you want to
    # create a camera state from within the interactive interface (this is also
    # possible).
    for camera_state in [
        "7_foot_overhead",
        "7_foot_offcenter",
        "rack",
    ]:
        interface.save(
            shot=shot,
            save_dir=output / camera_state,
            camera_state=camera_states[camera_state],
            file_prefix=camera_state,
            img_format="jpg",
            size=(480 * 1.6, 480),
            show_hud=False,
            fps=10,
            make_gif=True,
        )


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

    args = ap.parse_args()

    main(args)
