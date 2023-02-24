from pathlib import Path

import pooltool as pt
from pooltool.serialize import unstructure_to_json, structure_from_json, structure_from_msgpack, unstructure_to_msgpack
from pooltool.terminal import TimeCode

interface = pt.ShotViewer()

shot = pt.System(
    cue=pt.Cue(cue_ball_id="cue"),
    table=(table := pt.Table.pocket_table()),
    balls=pt.get_nine_ball_rack(table),
)

# Aim at the head ball then strike the cue ball
shot.aim_at_ball(ball_id="1")
shot.strike(V0=8)

# Evolve the shot
with TimeCode(success_msg="Simulated in "):
    pt.simulate(shot)

with TimeCode(success_msg="Continuized in "):
    shot.continuize()

interface.show(shot, title="Original shot")

json_path = Path(__file__).parent / "serialized_shot.json"
msgpack_path = Path(__file__).parent / "serialized_shot.msgpack"

with TimeCode(success_msg="Serialized to JSON in "):
    unstructure_to_json(shot, json_path)

with TimeCode(success_msg="Deserialized from JSON in "):
    json_hydrated = structure_from_json(json_path, pt.System)

with TimeCode(success_msg="Serialized to MSGPACK in "):
    unstructure_to_msgpack(shot, msgpack_path)

with TimeCode(success_msg="Deserialized from MSGPACK in "):
    msgpack_hydrated = structure_from_msgpack(msgpack_path, pt.System)

assert json_hydrated == msgpack_hydrated == shot

interface.show(json_hydrated, title="Serialized/deserialized shot")
