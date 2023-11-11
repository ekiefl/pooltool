from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Dict, List

import attrs

from pooltool import serialize
from pooltool.ani import model_dir

_expected_conversion_name = "conversion.json"


@attrs.define(frozen=True, slots=False)
class BallSet:
    name: str = attrs.field()

    @name.validator  # type: ignore
    def _check_name(self, _, value):
        path = (model_dir / "balls") / value
        if not path.exists() and not path.is_dir():
            raise ValueError(
                f"Invalid BallSet: '{value}'. {path} must exist as directory"
            )

    @property
    def path(self) -> Path:
        return (model_dir / "balls") / self.name

    @cached_property
    def conversion_dict(self) -> Dict[str, str]:
        conversion_path = self.path / _expected_conversion_name
        if conversion_path.exists():
            return serialize.conversion.structure_from(conversion_path, Dict[str, str])

        return {}

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
        if id in self.ids:
            return id

        if id in self.conversion_dict:
            return self.conversion_dict[id]

        raise ValueError(f"Ball ID '{id}' doesn't match to BallSet: {self.ids}")

    def ball_path(self, id: str) -> Path:
        model_id = self.ensure_valid(id)
        return self.path / f"{model_id}.glb"


ball_sets = {
    ball_dir.stem: BallSet(name=ball_dir.stem)
    for ball_dir in [path for path in (model_dir / "balls").glob("*") if path.is_dir()]
}


def get_ball_set(name: str) -> BallSet:
    assert name in ball_sets, f"Unknown ball set name: {name}"
    return ball_sets[name]
