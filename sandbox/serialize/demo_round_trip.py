"""Demos serialization and deserialization to/from JSON and/or MSGPACK"""

from pathlib import Path

import pooltool as pt
from pooltool.system import System

interface = pt.ShotViewer()

shot = System(
    cue=pt.Cue(cue_ball_id="cue"),
    table=(table := pt.Table.pocket_table()),
    balls=pt.get_nine_ball_rack(table, spacing_factor=1e-2),
)

# Aim at the head ball then strike the cue ball
shot.aim_at_ball(ball_id="1")
shot.strike(V0=8)

# Evolve the shot
pt.simulate(shot, inplace=True)

json_path = Path(__file__).parent / "serialized_shot.json"
msgpack_path = Path(__file__).parent / "serialized_shot.msgpack"

shot.save(json_path)
shot.save(msgpack_path)

json_hydrated = System.load(json_path)
msgpack_hydrated = System.load(msgpack_path)
assert json_hydrated == msgpack_hydrated == shot

interface.show(shot, title="Serialized/deserialized shot")
