#! /usr/bin/env python
"""This is a basic example of saving and loading a system state"""

import pooltool as pt
from pooltool.objects.ball.datatypes import BallHistory


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
    interface.show(new, title="A deepcopy of the original")


if __name__ == "__main__":
    main()
