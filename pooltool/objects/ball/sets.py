from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Protocol

import attrs

from pooltool.ani import model_dir


@attrs.define
class BallSet:
    name: str
    path: Path
    conversion: Optional[BallToModelConversion] = attrs.field(default=None)

    @property
    def ids(self) -> List[str]:
        return [path.stem for path in self.path.glob("*glb")]

    def ensure_valid(self, id: str) -> str:
        """Checks that Ball ID matches and return corresponding model ID

        Returns:
            model_id: The model ID associated with the passed ball ID

        Raises:
            ValueError if Ball ID doesn't match to BallSet
        """
        model_id = id if self.conversion is None else self.conversion(id)

        if model_id not in self.ids:
            raise ValueError(f"{model_id} doesn't match to BallSet: {self.ids}")

        return model_id

    def ball_path(self, id: str) -> Path:
        model_id = self.ensure_valid(id)
        return self.path / f"{model_id}.glb"


ball_sets = {
    ball_dir.stem: BallSet(name=ball_dir.stem, path=ball_dir)
    for ball_dir in [path for path in (model_dir / "balls").glob("*") if path.is_dir()]
}


def get_ball_set(name: str) -> BallSet:
    assert name in ball_sets, f"Unknown ball set name: {name}"
    return ball_sets[name]


# NOTE: If BallSet model IDs don't match ball IDs, you'll have to write a conversion and
# plop it in the `conversions` dictionary below
# --------------------------------------------------------------------------------------


class BallToModelConversion(Protocol):
    def __call__(self, ball_id: str) -> str:
        ...


conversions: Dict[str, BallToModelConversion] = {
    "generic_snooker": lambda ball_id: "red" if ball_id.startswith("red") else ball_id
}

for name, conversion in conversions.items():
    assert name in ball_sets
    ball_sets[name].conversion = conversion
