import json
from pathlib import Path
from typing import Any, Union

import msgpack
import msgpack_numpy as m
import numpy as np
from cattrs.preconf.json import make_converter

from pooltool.utils.strenum import StrEnum

Pathish = Union[str, Path]

converter = make_converter()

# Numpy arrays
# https://github.com/python-attrs/cattrs/issues/194
converter.register_structure_hook_func(
    lambda t: getattr(t, "__origin__", None) is np.ndarray,
    lambda v, t: np.array([t.__args__[1].__args__[0](e) for e in v]),
)
converter.register_unstructure_hook_func(
    lambda t: getattr(t, "__origin__", None) is np.ndarray,
    lambda array: array.tolist(),
)

# StrEnum
converter.register_unstructure_hook(
    StrEnum,
    lambda v: v.value,
)


def to_json(o: Any, path: Pathish) -> None:
    with open(path, "w") as fp:
        json.dump(o, fp, indent=2)


def from_json(path: Pathish) -> Any:
    with open(path, "r") as fp:
        return json.load(fp)


def to_msgpack(o: Any, path: Pathish) -> None:
    with open(path, "wb") as fp:
        fp.write(msgpack.packb(o, default=m.encode))


def from_msgpack(path: Pathish) -> Any:
    with open(path, "rb") as fp:
        return msgpack.unpackb(fp.read(), object_hook=m.decode)


def unstructure_to_json(dataclass: Any, path: Pathish) -> None:
    to_json(converter.unstructure(dataclass), path)


def structure_from_json(path: Pathish, cls) -> Any:
    return converter.structure(from_json(path), cls)
