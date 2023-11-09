from pathlib import Path
from typing import List

import attrs

from pooltool.ani import model_dir


@attrs.define(frozen=True)
class BallSet:
    name: str
    ids: List[str]
    path: Path

    def ball_path(self, id: str) -> Path:
        return self.path / f"{id}.glb"


ball_sets = {
    ball_dir.stem: BallSet(
        name=ball_dir.stem,
        ids=[path.stem for path in ball_dir.glob("*glb")],
        path=ball_dir,
    )
    for ball_dir in [path for path in (model_dir / "balls").glob("*") if path.is_dir()]
}


def get_ball_set(name: str) -> BallSet:
    assert name in ball_sets, f"Unknown ball set name: {name}"
    return ball_sets[name]
