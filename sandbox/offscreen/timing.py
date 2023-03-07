#! /usr/bin/env python
"""This illustrates the speed of reading/writing image versus array data"""

import argparse
import shutil
from pathlib import Path
from typing import Dict

import numpy as np

import pooltool as pt
from pooltool.ani.camera import camera_states
from pooltool.ani.image.io import (
    GzipArrayImages,
    ImageStorageMethod,
    ImageZip,
    NpyImages,
)
from pooltool.utils import human_readable_file_size

ap = argparse.ArgumentParser("A good old 9-ball break")
ap.add_argument(
    "--res",
    type=int,
    default=144,
    help="How resolved should the image be? E.g. 144, 360, 480, 720",
)
ap.add_argument(
    "--fps",
    type=int,
    default=10,
    help="How many frames per second?",
)
ap.add_argument(
    "--gray",
    action="store_true",
    help="Whether image is stored as grayscale",
)
ap.add_argument(
    "--seed",
    type=int,
    default=None,
    help="Provide a random seed if you want reproducible results",
)

args = ap.parse_args()

# -------------------------------------------------------------------------------------

interface = pt.ImageSaver()

if args.seed:
    np.random.seed(args.seed)

system = pt.System(
    cue=pt.Cue(cue_ball_id="cue"),
    table=(table := pt.Table.pocket_table()),
    balls=pt.get_nine_ball_rack(table, ordered=True, spacing_factor=1e-3),
)

# Aim at the head ball then strike the cue ball
system.aim_at_ball(ball_id="1")
system.strike(V0=8)

# Evolve the shot
with pt.terminal.TimeCode("Time to simulate 9-ball break: "):
    pt.simulate(system)

# -------------------------------------------------------------------------------------

# Make the output directory
path = Path(__file__).parent / "timing"
if path.exists():
    shutil.rmtree(path)
path.mkdir()

# Create the exporters
exporters: Dict[str, ImageStorageMethod] = {
    "image dir (PNG)": ImageZip(path / "png_images", ext="png", compress=False),
    "image zip (PNG)": ImageZip(path / "png_images.zip", ext="png"),
    "image dir (JPG)": ImageZip(path / "jpg_images", ext="jpg", compress=False),
    "image zip (JPG)": ImageZip(path / "jpg_images.zip", ext="jpg"),
    "npy": NpyImages(path / "image_array.npy"),
    "gzip array": GzipArrayImages(path / "images.array.gz"),
}

# Generate the image data
with pt.terminal.TimeCode("Time to render the images: "):
    datapack = interface.gen_datapack(
        shot=system,
        camera_state=camera_states["7_foot_overhead_zoom"],
        size=(args.res * 1.6, args.res),
        show_hud=False,
        gray=args.gray,
        fps=args.fps,
    )

# Set to none to avoid being calculated in storage format sizes
datapack.system = None

# -------------------------------------------------------------------------------------


def _dir_size(path):
    return human_readable_file_size(
        sum(file.stat().st_size for file in path.glob(f"*.{exporter.ext}"))
    )


run = pt.terminal.Run()

for name, exporter in exporters.items():
    run.warning("", header=f"{name} read/write/disk stats")

    with pt.terminal.TimeCode(f"Time to write {name}: "):
        exporter.save(datapack)

    with pt.terminal.TimeCode(f"Time to read {name}: "):
        exporter.read(exporter.path)

    if name in ("image dir (PNG)", "image dir (JPG)"):
        assert isinstance(exporter, ImageZip)
        size = _dir_size(Path(exporter.path))
    else:
        size = human_readable_file_size(exporter.path.stat().st_size)

    run.info(f"Size of {name}", size, nl_before=1, nl_after=1)
