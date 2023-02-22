#! /usr/bin/env python

import numpy as np

import pooltool as pt

# Setup a shot
system = pt.System(
    cue=pt.Cue(cue_ball_id="cue", phi=225, V0=2),
    table=(table := pt.Table.default()),
    balls={
        "cue": pt.Ball.create("cue", xy=(table.w / 2, table.l / 3)),
        "1": pt.Ball.create("1", xy=(table.w / 4, table.l * 0.2)),
    },
)

collection = pt.MultiSystem()

for x in np.linspace(0, 0.7, 20):
    shot = system.copy()
    shot.cue.set_state(b=-x)
    shot.strike()
    pt.simulate(shot)
    collection.append(shot)

interface = pt.ShotViewer()
interface.show(collection)
