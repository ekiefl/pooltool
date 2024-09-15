#! /usr/bin/env python

from pathlib import Path

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
    pt.simulate(shot, inplace=True)
    collection.append(shot)

# Just showing off that you can save and load the multisystem
json_path = Path(__file__).parent / "collection.json"
collection.save(json_path)
new_collection = pt.MultiSystem.load(json_path)

for old_system, new_system in zip(collection.multisystem, new_collection.multisystem):
    assert old_system == new_system

pt.show(new_collection)
