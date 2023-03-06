#! /usr/bin/env python
"""This illustrates the speed of reading/writing image versus array data"""

import argparse
import shutil
import timeit
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

trials = 1

# Evolve the shot
simulate_time = timeit.timeit("pt.simulate(system)", globals=globals(), number=trials)
print(f"Average time to simulate 9-ball break (intensive): {simulate_time/trials}")

# Make the output directory
path = Path(__file__).parent / "timing"
if path.exists():
    shutil.rmtree(path)
path.mkdir()

# Create the exporters
npy_exporter = NpyImages(path / "image_array.npy")
img_exporter = ImageDir(path / "image_dir", ext="png", save_gif=True)

# Generate the image data
s = """\
datapack = interface.gen_datapack(
    shot=system,
    camera_state=camera_states["7_foot_overhead_zoom"],
    size=(args.res * 1.6, args.res),
    show_hud=False,
    fps=10,
)
"""
gen_images = timeit.timeit(s, globals=globals(), number=trials)
print(f"Average time to render the images: {gen_images/trials}")

datapack = interface.gen_datapack(
    shot=system,
    camera_state=camera_states["7_foot_overhead_zoom"],
    size=(args.res * 1.6, args.res),
    show_hud=False,
    fps=10,
)

npy_write_time = timeit.timeit(
    "npy_exporter.save(datapack)", globals=globals(), number=trials
)
print(f"Average time to write npy file: {npy_write_time/trials}")

npy_read_time = timeit.timeit(
    "NpyImages.read(npy_exporter.path)", globals=globals(), number=trials
)
print(f"Average time to read npy file: {npy_read_time/trials}")

npy_size = human_readable_file_size(npy_exporter.path.stat().st_size)
print(f"Size of npy file: {npy_size}")

img_write_time = timeit.timeit(
    "img_exporter.save(datapack)", globals=globals(), number=trials
)
print(f"Average time to write image dir: {img_write_time/trials}")

img_read_time = timeit.timeit(
    "ImageDir.read(img_exporter.path)", globals=globals(), number=trials
)
print(f"Average time to read image dir: {img_read_time/trials}")

dir_size = human_readable_file_size(
    sum(file.stat().st_size for file in Path(img_exporter.path).rglob("*"))
)
print(f"Size of image dir: {dir_size}")
