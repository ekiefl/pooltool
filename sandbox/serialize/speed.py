"""Demos serialization and deserialization to/from JSON and/or MSGPACK"""

from pathlib import Path

import numpy as np

import pooltool as pt
from pooltool.system import System
from pooltool.terminal import TimeCode

np.random.seed(42)

shot = System(
    cue=pt.Cue(cue_ball_id="cue"),
    table=(table := pt.Table.default()),
    balls=pt.get_rack(pt.GameType.NINEBALL, table, spacing_factor=1e-2),
)

# Aim at the head ball
shot.strike(V0=8, phi=pt.aim.at_ball(shot, "1"))

# Evolve the shot
pt.simulate(shot, inplace=True)
pt.continuize(shot, inplace=True)

json_path = Path(__file__).parent / "serialized_shot.json"
msgpack_path = Path(__file__).parent / "serialized_shot.msgpack"

N = 100

with TimeCode(success_msg=f"Serialized {N} shots to JSON in "):
    for _ in range(N):
        shot.save(json_path, drop_continuized_history=True)

with TimeCode(success_msg=f"Deserialized {N} shots from JSON in "):
    for _ in range(N):
        System.load(json_path)

with TimeCode(success_msg=f"Serialized {N} shots to MSGPACK in "):
    for _ in range(N):
        shot.save(msgpack_path, drop_continuized_history=True)

with TimeCode(success_msg=f"Deserialized {N} shots from MSGPACK in "):
    for _ in range(N):
        System.load(msgpack_path)
