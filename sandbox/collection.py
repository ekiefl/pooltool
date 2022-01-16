#! /usr/bin/env python

import numpy as np
import pooltool as pt

# Setup a shot
table = pt.PocketTable()
balls = {
    'cue': pt.Ball('cue', xyz = (table.w/2, table.l/2, pt.R)),
    '1': pt.Ball('1', xyz = (table.w/4, table.l/4, pt.R)),
}
cue = pt.Cue(cueing_ball=balls['cue'])
cue.aim_at_ball(balls['1'])
system = pt.System(cue=cue, table=table, balls=balls)

collection = pt.SystemCollection()

for dphi in np.linspace(0,2,20):
    shot = system.copy()
    shot.cue.set_state(phi = shot.cue.phi + dphi)
    shot.cue.strike()
    shot.simulate()
    collection.append(shot)

interface = pt.ShotViewer()
interface.show(collection)
