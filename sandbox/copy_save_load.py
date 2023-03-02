#! /usr/bin/env python
"""This is a basic example of saving and loading a system state"""

import tempfile
from pathlib import Path

import pooltool as pt


def main():
    # Initialize the GUI
    interface = pt.ShotViewer()

    # Create a system
    shot = pt.System(
        table=(table := pt.Table.pocket_table()),
        balls=pt.get_nine_ball_rack(table, ordered=True),
        cue=pt.Cue(cue_ball_id="cue"),
    )
    shot.aim_at_ball(ball_id="1")
    shot.strike(V0=8)

    # Simulate
    pt.simulate(shot)

    # Visualize it
    interface.show(shot, title="Original system state")

    # You can copy it and visualize the copy
    new = shot.copy()
    interface.show(new, title="A deep-ish copy of the original")

    # You can also save it to a file, and load it up again.
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "shot.json"
        new.save(path)
        newer = pt.System.load(path)

    interface.show(newer, title="A copy of the original, loaded from the disk space")


if __name__ == "__main__":
    main()
