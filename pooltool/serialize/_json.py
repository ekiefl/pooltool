import json
from typing import Any

from pooltool.serialize._cattrs import converter
from pooltool.serialize.types import Pathish


def to_json(o: Any, path: Pathish) -> None:
    with open(path, "w") as fp:
        json.dump(o, fp, indent=4)


def from_json(path: Pathish) -> Any:
    with open(path, "r") as fp:
        return json.load(fp)


def unstructure_to_json(dataclass: Any, path: Pathish) -> None:
    to_json(converter.unstructure(dataclass), path)


def structure_from_json(path: Pathish, cls) -> Any:
    return converter.structure(from_json(path), cls)
