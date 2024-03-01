"""Ballset module

**What is a ballset?**

A ballset specifies the set that a ball belongs to.

**Why is it important?**

Ballsets are important for properly rendering balls in a scene. By specifying a ballset
for a ball, you declare the visual texture / skin that the ball should be wrapped in. If
a ball's ballset is not declared, it will be rendered with the default skin.

**What ballsets are available?**

See :func:`get_ballset_names`.

**Where are ballsets stored?**

Each ballset is represented as a subdirectory within the following directory:

.. code::

    $ echo $(python -c "import pooltool; print(pooltool.__file__[:-12])")/models/balls

Each ball model is a ``.glb`` file. Its base name represents the model's ID, and
matching ball IDs will be textured by this model. To associate multiple ball IDs to the
same model, a ``conversion.json`` file is used. For example, see how the
``generic_snooker`` ballset matches the red ball IDs to the same model ID:

.. code::

    $ cat $(python -c "import pooltool; print(pooltool.__file__[:-12])")/models/balls/generic_snooker/conversion.json
    {
      "red_01": "red",
      "red_02": "red",
      "red_03": "red",
      "red_04": "red",
      "red_05": "red",
      "red_06": "red",
      "red_07": "red",
      "red_08": "red",
      "red_09": "red",
      "red_10": "red",
      "red_11": "red",
      "red_12": "red",
      "red_13": "red",
      "red_14": "red",
      "red_15": "red"
    }
"""

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
    """A ballset

    Attributes:
        name:
            The name of the ballset.

            During instantiation, the validity of this name will be checked, and a
            ValueError will be raised if the ballset doesn't exist.
    """

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
        """The path of the ballset directory

        This directory holds the ball models.
        """
        return (model_dir / "balls") / self.name

    @cached_property
    def _conversion_dict(self) -> Dict[str, str]:
        conversion_path = self.path / _expected_conversion_name
        if conversion_path.exists():
            return serialize.conversion.structure_from(conversion_path, Dict[str, str])

        return {}

    @property
    def ids(self) -> List[str]:
        return [path.stem for path in self.path.glob("*glb")]

    def _ensure_valid(self, id: str) -> str:
        """Checks that Ball ID matches to a model in in ballset.

        Args:
            id: The ball ID.

        Raises:
            ValueError: If Ball ID doesn't match to BallSet.

        Returns:
            model_id: The model ID associated with the passed ball ID.
        """
        if id in self.ids:
            return id

        if id in self._conversion_dict:
            return self._conversion_dict[id]

        raise ValueError(f"Ball ID '{id}' doesn't match to BallSet: {self.ids}")

    def ball_path(self, id: str) -> Path:
        """The model path used for a given ball ID

        Args:
            id: The ball ID.

        Raises:
            ValueError: If Ball ID doesn't match to the ballset.

        Returns:
            Path:
                The model path.
        """
        model_id = self._ensure_valid(id)
        return self.path / f"{model_id}.glb"


ballsets = {
    ball_dir.stem: BallSet(name=ball_dir.stem)
    for ball_dir in [path for path in (model_dir / "balls").glob("*") if path.is_dir()]
}


def get_ballset(name: str) -> BallSet:
    """Return the ballset with the given name.

    Args:
        name:
            The name of the ballset. To list available ballset names, call
            :func:`get_ballset_names`.

    Raises:
        ValueError: If Ball ID doesn't match to the ballset.

    Returns:
        BallSet: A ballset.
    """
    assert (
        name in ballsets
    ), f"Unknown ballset name: {name}, available: {get_ballset_names()}"
    return ballsets[name]


def get_ballset_names() -> List[str]:
    """Returns a list of available ballset names"""
    return list(ballsets.keys())
