from pathlib import Path

import pooltool as pt
from pooltool.serialize import unstructure_to_json

shot = pt.System(
    cue=pt.Cue(cue_ball_id="cue"),
    table=(table := pt.Table.pocket_table()),
    balls=pt.get_nine_ball_rack(table),
)

# Aim at the head ball then strike the cue ball
shot.aim_at_ball(ball_id="1")
shot.strike(V0=6)

# Evolve the shot
pt.simulate(shot)

unstructure_to_json(shot, Path(__file__).parent / "serialized_shot.json")
