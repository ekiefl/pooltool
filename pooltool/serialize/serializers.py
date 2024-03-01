import json
from pathlib import Path
from typing import Any, Callable, Dict, Union

import msgpack
import msgpack_numpy as m
import yaml

from pooltool.utils.strenum import StrEnum, auto

Pathish = Union[str, Path]


class SerializeFormat(StrEnum):
    JSON = auto()
    MSGPACK = auto()
    YAML = auto()

    @property
    def ext(self):
        return self.value


def to_json(o: Any, path: Pathish) -> None:
    with open(path, "w") as fp:
        json.dump(o, fp, indent=2)


def from_json(path: Pathish) -> Any:
    with open(path, "r") as fp:
        return json.load(fp)


def to_yaml(o: Any, path: Pathish) -> None:
    with open(path, "w") as fp:
        yaml.dump(o, fp)


def from_yaml(path: Pathish) -> Any:
    with open(path, "r") as fp:
        return yaml.safe_load(fp)


def to_msgpack(o: Any, path: Pathish) -> None:
    with open(path, "wb") as fp:
        packed = msgpack.packb(o, default=m.encode)
        assert isinstance(packed, bytes), "msgpack.packb must return bytes"
        fp.write(packed)


def from_msgpack(path: Pathish) -> Any:
    with open(path, "rb") as fp:
        return msgpack.unpackb(fp.read(), object_hook=m.decode)


serializers: Dict[SerializeFormat, Callable[[Any, Pathish], None]] = {
    SerializeFormat.JSON: to_json,
    SerializeFormat.MSGPACK: to_msgpack,
    SerializeFormat.YAML: to_yaml,
}

deserializers: Dict[SerializeFormat, Callable[[Pathish], Any]] = {
    SerializeFormat.JSON: from_json,
    SerializeFormat.MSGPACK: from_msgpack,
    SerializeFormat.YAML: from_yaml,
}
