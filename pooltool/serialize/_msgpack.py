from typing import Any

import msgpack
import msgpack_numpy as m

from pooltool.serialize.types import Pathish


def to_msgpack(o: Any, path: Pathish) -> None:
    with open(path, "wb") as fp:
        fp.write(msgpack.packb(o, default=m.encode))


def from_msgpack(path: Pathish) -> Any:
    with open(path, "rb") as fp:
        return msgpack.unpackb(fp.read(), object_hook=m.decode)
