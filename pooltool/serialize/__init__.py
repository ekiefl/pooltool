import json
from pathlib import Path
from typing import Any, Union

import msgpack
import msgpack_numpy as m
import numpy as np
from cattrs.preconf.json import make_converter as make_json_converter
from cattrs.preconf.msgpack import make_converter as make_msgpack_converter
from attrs import define, field

from pooltool.utils.strenum import StrEnum


converter_json = make_json_converter()
converter_msgpack = make_msgpack_converter()

# Numpy arrays
# https://github.com/python-attrs/cattrs/issues/194
# JSON needs to unstructure numpy arrays as lists, but msgpack doesn't thanks to
# msgpack-numpy
converter_json.register_structure_hook_func(
    lambda t: getattr(t, "__origin__", None) is np.ndarray,
    lambda v, t: np.array([t.__args__[1].__args__[0](e) for e in v]),
)
converter_json.register_unstructure_hook_func(
    lambda t: getattr(t, "__origin__", None) is np.ndarray,
    lambda array: array.tolist(),
)
converter_msgpack.register_structure_hook_func(
    lambda t: getattr(t, "__origin__", None) is np.ndarray,
    lambda v, t: np.array([t.__args__[1].__args__[0](e) for e in v]),
)

# StrEnum
converter_json.register_unstructure_hook(
    StrEnum,
    lambda v: v.value,
)
converter_msgpack.register_unstructure_hook(
    StrEnum,
    lambda v: v.value,
)

Pathish = Union[str, Path]

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
    to_json(converter_json.unstructure(dataclass), path)


def structure_from_json(path: Pathish, cls) -> Any:
    return converter_json.structure(from_json(path), cls)


def unstructure_to_msgpack(dataclass: Any, path: Pathish) -> None:
    to_msgpack(converter_msgpack.unstructure(dataclass), path)


def structure_from_msgpack(path: Pathish, cls) -> Any:
    return converter_msgpack.structure(from_msgpack(path), cls)
