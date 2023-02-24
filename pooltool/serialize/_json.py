import json
from typing import Any

from pooltool.serialize.types import Pathish


def to_json(o: Any, path: Pathish) -> None:
    with open(path, "w") as fp:
        json.dump(o, fp, indent=4)


def from_json(path: Pathish) -> Any:
    with open(path, "r") as fp:
        return json.load(fp)
