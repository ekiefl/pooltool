from __future__ import annotations

from enum import Enum, auto
from typing import Any, TypeVar

__all__ = ["auto", "StrEnum"]

_S = TypeVar("_S", bound="StrEnum")


class StrEnum(str, Enum):
    """
    Enum where members are also (and must be) strings
    """

    def __new__(cls: type[_S], *values: str) -> _S:
        if len(values) > 3:
            raise TypeError(f"too many arguments for str(): {values!r}")
        if len(values) == 1:
            # it must be a string
            if not isinstance(values[0], str):
                raise TypeError(f"{values[0]!r} is not a string")
        if len(values) >= 2:
            # check that encoding argument is a string
            value = values[1]  # type: ignore
            if not isinstance(value, str):
                raise TypeError(f"encoding must be a string, not {value!r}")
        if len(values) == 3:
            # check that errors argument is a string
            if not isinstance(values[2], str):
                raise TypeError(f"errors must be a string, not {values[2]!r}")
        value = str(*values)
        member = str.__new__(cls, value)
        member._value_ = value
        return member

    __str__ = str.__str__  # type: ignore

    @staticmethod
    def _generate_next_value_(
        name: str, start: int, count: int, last_values: list[Any]
    ) -> str:
        """
        Return the lower-cased version of the member name.
        """
        return name.lower()
