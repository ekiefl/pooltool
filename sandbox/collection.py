#! /usr/bin/env python

import numpy as np

import pooltool as pt

# Setup a shot
table = pt.PocketTable(model_name="7_foot")
balls = {
    "cue": pt.Ball("cue", xyz=(table.w / 2, table.l / 3, pt.R)),
    "1": pt.Ball("1", xyz=(table.w / 4, table.l * 0.2, pt.R)),
}
cue = pt.Cue(cueing_ball=balls["cue"])
cue.set_state(phi=225, V0=2)
system = pt.System(cue=cue, table=table, balls=balls)

collection = pt.SystemCollection()

for x in np.linspace(0, 0.7, 20):
    shot = system.copy()
    shot.cue.set_state(b=-x)
    shot.cue.strike()
    shot.simulate()
    collection.append(shot)

interface = pt.ShotViewer()
interface.show(collection)
