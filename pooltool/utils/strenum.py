from enum import Enum, auto
from typing import Any, List, Type, TypeVar

__all__ = ["auto"]

_S = TypeVar("_S", bound="StrEnum")


class StrEnum(str, Enum):
    """
    Enum where members are also (and must be) strings
    """

    def __new__(cls: Type[_S], *values: str) -> _S:
        if len(values) > 3:
            raise TypeError("too many arguments for str(): %r" % (values,))
        if len(values) == 1:
            # it must be a string
            if not isinstance(values[0], str):
                raise TypeError("%r is not a string" % (values[0],))
        if len(values) >= 2:
            # check that encoding argument is a string
            value = values[1]  # type: ignore
            if not isinstance(value, str):
                raise TypeError("encoding must be a string, not %r" % (value,))
        if len(values) == 3:
            # check that errors argument is a string
            if not isinstance(values[2], str):
                raise TypeError("errors must be a string, not %r" % (values[2]))
        value = str(*values)
        member = str.__new__(cls, value)
        member._value_ = value
        return member

    __str__ = str.__str__  # type: ignore

    @staticmethod
    def _generate_next_value_(
        name: str, start: int, count: int, last_values: List[Any]
    ) -> str:
        """
        Return the lower-cased version of the member name.
        """
        return name.lower()
