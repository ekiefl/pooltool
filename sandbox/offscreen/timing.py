#! /usr/bin/env python
"""This illustrates the speed of reading/writing image versus array data"""

try:
    import matplotlib.pyplot as plt
except ImportError:
    raise ImportError(
        "This script requires matplotlib. `pip install matplotlib` if interested"
    )

import argparse
import shutil
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

import pooltool as pt
from pooltool.ani.camera import camera_states
from pooltool.ani.image.interface import FrameStepper, image_stack
from pooltool.ani.image.io import (
    GzipArrayImages,
    HDF5Images,
    ImageStorageMethod,
    ImageZip,
    NpyImages,
)

ap = argparse.ArgumentParser("A good old 9-ball break")
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
    default=42,
    help="Provide a random seed if you want reproducible results",
)

args = ap.parse_args()


def _dir_size(path):
    return sum(file.stat().st_size for file in path.glob(f"*.{exporter.ext}"))


# -------------------------------------------------------------------------------------


stepper = FrameStepper()

if args.seed:
    np.random.seed(args.seed)

system = pt.System(
    cue=pt.Cue(cue_ball_id="cue"),
    table=(table := pt.Table.default()),
    balls=pt.get_rack(pt.GameType.NINEBALL, table, spacing_factor=1e-3),
)

# Aim at the head ball
system.strike(V0=8, phi=pt.aim.at_ball(system, "1"))

# Simulate the system once to load cached numba functions
pt.simulate(system, inplace=False)

# Time shot simulation
with pt.terminal.TimeCode(quiet=True) as t:
    pt.simulate(system, inplace=True)
sim_time = t.time.total_seconds()

# -------------------------------------------------------------------------------------


def clear_and_make_dir():
    # Make the output directory
    if path.exists():
        shutil.rmtree(path)
    path.mkdir()


path = Path(__file__).parent / "timing"
clear_and_make_dir()

# Create the exporters
exporters: Dict[str, ImageStorageMethod] = {
    "HDF5 uncompressed": HDF5Images(path / "images.hdf5"),
    "image dir (PNG)": ImageZip(path / "png_images", ext="png", compress=False),
    "image zip (PNG)": ImageZip(path / "png_images.zip", ext="png"),
    "image dir (JPG)": ImageZip(path / "jpg_images", ext="jpg", compress=False),
    "image zip (JPG)": ImageZip(path / "jpg_images.zip", ext="jpg"),
    "npy": NpyImages(path / "image_array.npy"),
    "gzip array": GzipArrayImages(path / "images.array.gz"),
}

# Initialize the time data
stats: Dict[str, List[float]] = {}
stats["resolution"] = []
stats["frames"] = []
stats["gray"] = []
stats["fps"] = []
stats["simulate"] = []
stats["gen image"] = []
for name in exporters:
    stats[name + " read"] = []
for name in exporters:
    stats[name + " write"] = []
for name in exporters:
    stats[name + " size"] = []

# -------------------------------------------------------------------------------------

# Run one to avoid cache loading
image_stack(
    system,
    stepper,
    size=(int(80 * 1.6), 80),
    fps=args.fps,
    gray=args.gray,
    show_hud=False,
)

run = pt.terminal.Run()
resolutions = [80, 144, 240, 360, 480, 720, 1080]

for res in resolutions:
    stats["resolution"].append(res)
    stats["simulate"].append(sim_time)
    stats["fps"].append(args.fps)
    stats["gray"].append(args.gray)

    with pt.terminal.TimeCode(quiet=True) as t:
        imgs = image_stack(
            system=system,
            interface=stepper,
            camera_state=camera_states["7_foot_overhead"],
            size=(int(res * 1.6), res),
            fps=args.fps,
            gray=args.gray,
            show_hud=False,
        )

    stats["gen image"].append(t.time.total_seconds())
    stats["frames"].append(np.shape(imgs)[0])

    for name, exporter in exporters.items():
        with pt.terminal.TimeCode(quiet=True) as t:
            exporter.save(imgs)
        stats[name + " write"].append(t.time.total_seconds())

        with pt.terminal.TimeCode(quiet=True) as t:
            exporter.read(exporter.path)
        stats[name + " read"].append(t.time.total_seconds())

        if name in ("image dir (PNG)", "image dir (JPG)"):
            assert isinstance(exporter, ImageZip)
            size = _dir_size(Path(exporter.path))
        else:
            size = exporter.path.stat().st_size

        stats[name + " size"].append(size / 1e6)

    clear_and_make_dir()

results_path = Path(__file__).parent / "timing_results"
results_path.mkdir(exist_ok=True)

results = pd.DataFrame(stats)


def plot(x, y, ax, log=True):
    results.plot(x=x, y=y, ax=ax, kind="scatter", logy=log)
    results.plot(x=x, y=y, ax=ax, kind="line", logy=log)


fig, ax = plt.subplots()

plot(x="resolution", y="image zip (JPG) size", ax=ax)
plot(x="resolution", y="image zip (PNG) size", ax=ax)
plot(x="resolution", y="npy size", ax=ax)
plot(x="resolution", y="gzip array size", ax=ax)
plt.ylabel("Size [mb]")

plt.savefig(results_path / "size.png")
fig, ax = plt.subplots()

plot(x="resolution", y="image zip (JPG) read", ax=ax)
plot(x="resolution", y="image zip (PNG) read", ax=ax)
plot(x="resolution", y="npy read", ax=ax)
plot(x="resolution", y="gzip array read", ax=ax)
plt.ylabel("Read time [s]")

plt.savefig(results_path / "read.png")
fig, ax = plt.subplots()

plot(x="resolution", y="image zip (JPG) write", ax=ax)
plot(x="resolution", y="image zip (PNG) write", ax=ax)
plot(x="resolution", y="npy write", ax=ax)
plot(x="resolution", y="gzip array write", ax=ax)
plt.ylabel("Write time [s]")

plt.savefig(results_path / "write.png")

results.to_csv(results_path / "timing_results.txt", sep="\t")
