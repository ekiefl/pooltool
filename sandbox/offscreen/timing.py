#! /usr/bin/env python
"""This illustrates the speed of reading/writing image versus array data"""

import argparse
import shutil
from pathlib import Path

import numpy as np

import pooltool as pt
from pooltool.ani.camera import camera_states
from pooltool.ani.image.io import ImageDir, NpyImages
from pooltool.utils import human_readable_file_size

ap = argparse.ArgumentParser("A good old 9-ball break")
ap.add_argument(
    "--res",
    type=int,
    default=80,
    help="How resolved should the image be? E.g. 144, 360, 480, 720",
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

# Make the output directory
path = Path(__file__).parent / "timing"
if path.exists():
    shutil.rmtree(path)
path.mkdir()

# Create the exporters
npy_exporter = NpyImages(path / "image_array.npy")
img_exporter = ImageDir(path / "image_dir", ext="png", save_gif=True)

# Generate the image data
with pt.terminal.TimeCode("Time to render the images: "):
    datapack = interface.gen_datapack(
        shot=system,
        camera_state=camera_states["7_foot_overhead_zoom"],
        size=(args.res * 1.6, args.res),
        show_hud=False,
        fps=10,
    )

with pt.terminal.TimeCode("Time to write npy file: "):
    npy_exporter.save(datapack)

with pt.terminal.TimeCode("Time to read npy file: "):
    NpyImages.read(npy_exporter.path)

with pt.terminal.TimeCode("Time to write img directory: "):
    img_exporter.save(datapack)

with pt.terminal.TimeCode("Time to read img directory: "):
    ImageDir.read(img_exporter.path)

run = pt.terminal.Run()

run.info(
    "Size of npy file",
    human_readable_file_size(npy_exporter.path.stat().st_size),
    nl_before=1,
)
run.info(
    "Size of image directory",
    human_readable_file_size(
        sum(file.stat().st_size for file in Path(img_exporter.path).glob("*.png"))
    ),
)
