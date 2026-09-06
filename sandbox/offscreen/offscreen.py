#! /usr/bin/env python
"""This illustrates how to render offscreen and save as images"""

import shutil
from pathlib import Path

import numpy as np

import pooltool as pt
from pooltool.ani.camera import camera_states
from pooltool.ani.image import HDF5Images, ImageZip, NpyImages, image_stack
from pooltool.ani.image.interface import FrameStepper


def main(args):
    stepper = FrameStepper()

    if args.seed:
        np.random.seed(args.seed)

    system = pt.System(
        cue=pt.Cue(cue_ball_id="cue"),
        table=(table := pt.Table.default()),
        balls=pt.get_rack(
            pt.GameType.NINEBALL, table, spacing_factor=args.spacing_factor
        ),
    )

    # Aim at the head ball
    system.strike(V0=args.V0, phi=pt.aim.at_ball(system, "1"))

    # Evolve the shot
    pt.simulate(system, inplace=True)

    # Make an dump dir
    path = Path(__file__).parent / "offscreen_out"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir()

    # These camera states can be found in pooltool/ani/camera/camera_states. You can
    # make your own by creating a new JSON in that directory. Reach out if you want to
    # create a camera state from within the interactive interface (this is also
    # possible).
    for camera_state in [
        "7_foot_overhead",
        "7_foot_offcenter",
    ]:
        if args.exporter == "dir":
            exporter = ImageZip(path / f"{camera_state}.zip", ext="png")
        elif args.exporter == "h5":
            exporter = HDF5Images(path / f"{camera_state}.h5")
        elif args.exporter == "npy":
            exporter = NpyImages(path / f"{camera_state}.npy")

        imgs = image_stack(
            system=system,
            interface=stepper,
            size=(360 * 1.6, 360),
            fps=10,
            camera_state=camera_states[camera_state],
            show_hud=False,
            gray=False,
        )
        exporter.save(imgs)

        # Verify the images can be read back
        read_from_disk = exporter.read(exporter.path)
        assert np.array_equal(imgs, read_from_disk)


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
        "--exporter",
        type=str,
        default="dir",
        choices=("h5", "dir", "npy"),
        help="Which export strategy do you want to use?",
    )
    ap.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Provide a random seed if you want reproducible results",
    )

    args = ap.parse_args()

    main(args)
