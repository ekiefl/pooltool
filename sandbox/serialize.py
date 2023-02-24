from pathlib import Path

import pooltool as pt
from pooltool.serialize import unstructure_to_json, structure_from_json

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
pt.simulate(shot)

interface.show(shot, title="Original shot")

path = Path(__file__).parent / "serialized_shot.json"
unstructure_to_json(shot, path)
new = structure_from_json(path, pt.System)

assert new == shot

interface.show(new, title="Serialized/deserialized shot")
