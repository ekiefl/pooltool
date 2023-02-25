from pathlib import Path

import pooltool as pt
from pooltool.system import System
from pooltool.terminal import TimeCode

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
with TimeCode(success_msg="Simulated in "):
    pt.simulate(shot)

json_path = Path(__file__).parent / "serialized_shot.json"
msgpack_path = Path(__file__).parent / "serialized_shot.msgpack"

with TimeCode(success_msg="Serialized to JSON in "):
    shot.save(json_path)

with TimeCode(success_msg="Deserialized from JSON in "):
    json_hydrated = System.load(json_path)

with TimeCode(success_msg="Serialized to MSGPACK in "):
    shot.save(msgpack_path)

with TimeCode(success_msg="Deserialized from MSGPACK in "):
    msgpack_hydrated = System.load(msgpack_path)

assert json_hydrated == msgpack_hydrated == shot

interface.show(json_hydrated, title="Serialized/deserialized shot")
