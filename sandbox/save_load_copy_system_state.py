#! /usr/bin/env python
"""This is a basic example of saving and loading a system state"""

import pooltool as pt

import tempfile

def main():
    # Initialize the GUI
    interface = pt.ShotViewer()

    # Create a system state
    table = pt.PocketTable(model_name='7_foot')
    balls = pt.get_nine_ball_rack(table, ordered=True)
    cue = pt.Cue(cueing_ball=balls['cue'])

    # Set up a shot
    shot = pt.System(cue=cue, table=table, balls=balls)
    shot.cue.aim_at_ball(shot.balls['1'])
    shot.cue.strike(V0=8)

    # Now instead of simulating, save the system as a pickle file
    filepath = pt.utils.get_temp_file_path()
    shot.save(filepath)

    # Ok now make a new system and attach the old state
    shot2 = pt.System()
    shot2.load(filepath)

    # Now simulate the first
    shot.simulate(continuize=True)
    interface.show(shot, title='Original system state')

    # Now simulate the second
    shot2.simulate(continuize=True)
    interface.show(shot2, title='Pickled system state')

    # Now make a copy of the second. This is a 'deep' copy, and
    # uses the same underlying methods that created shot2
    shot3 = shot2.copy()
    interface.show(shot3, title='Copied system state')

if __name__ == '__main__':
    main()
