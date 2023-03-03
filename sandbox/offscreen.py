#! /usr/bin/env python
"""This illustrates how to render offscreen and save as images"""

import shutil
from pathlib import Path

import numpy as np

import pooltool as pt
from pooltool.ani.camera import camera_states
from pooltool.ani.image.exporters import HDF5Exporter


def main(args):
    interface = pt.ImageSaver()

    if args.seed:
        np.random.seed(args.seed)

    system = pt.System(
        cue=pt.Cue(cue_ball_id="cue"),
        table=(table := pt.Table.pocket_table()),
        balls=pt.get_nine_ball_rack(
            table, ordered=True, spacing_factor=args.spacing_factor
        ),
    )

    # Aim at the head ball then strike the cue ball
    system.aim_at_ball(ball_id="1")
    system.strike(V0=args.V0)

    # Evolve the shot
    pt.simulate(system)

    save_dir = Path(__file__).parent / "offscreen_out"
    if save_dir.exists():
        shutil.rmtree(save_dir)

    # These camera states can be found in pooltool/ani/camera/camera_states. You can
    # make your own by creating a new JSON in that directory. Reach out if you want to
    # create a camera state from within the interactive interface (this is also
    # possible).
    for camera_state in [
        "7_foot_overhead",
        "7_foot_offcenter",
        "rack",
    ]:
        exporter = pt.ImageDirExporter(
            save_dir / camera_state, ext="jpg", save_gif=True
        )

        interface.save(
            shot=system,
            exporter=exporter,
            camera_state=camera_states[camera_state],
            size=(360 * 1.6, 360),
            show_hud=False,
            fps=5,
        )


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser("A good old 9-ball break")
    ap.add_argument(
        "--spacing-factor",
        type=float,
        default=1e-3,
        help="What fraction of the ball radius should each ball be randomly separated "
        "by in the rack?",
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
