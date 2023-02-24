import numpy as np
import pytest
from attrs import define
from numpy.typing import NDArray

from pooltool.serialize import converter
from pooltool.utils.dataclasses import are_dataclasses_equal
from pooltool.utils.strenum import StrEnum, auto


@define
class ImNested:
    a: bool
    b: int
    c: str


@define
class StandardTypes:
    a: ImNested
    b: float
    c: set
    d: list


@define(eq=False)
class WithNumpyArray:
    array: NDArray[np.float64]

    def __eq__(self, other):
        return are_dataclasses_equal(self, other)


class Categories(StrEnum):
    one = auto()
    two = auto()
    three = auto()


@pytest.fixture
def standard_obj():
    return StandardTypes(
        a=ImNested(a=True, b=42, c="foo"),
        b=47.0,
        c={1, 2, 3},
        d=[4, 3, 2, 1],
    )


@pytest.fixture
def numpy_obj(standard_obj):
    return WithNumpyArray(
        a=standard_obj.a,
        b=standard_obj.b,
        c=standard_obj.c,
        d=standard_obj.d,
        e=np.arange(9, dtype=np.float64).reshape((3, 3)),
    )


def test_standard(standard_obj):
    """Test unstructure/structure round trip with standard types"""
    assert standard_obj == converter.structure(
        converter.unstructure(standard_obj), StandardTypes
    )
    assert numpy_obj == converter.structure(
        converter.unstructure(numpy_obj), WithNumpyArray
    )


def test_numpy(numpy_obj):
    """Test unstructure/structure round trip with numpy types"""
    assert numpy_obj == converter.structure(
        converter.unstructure(numpy_obj), WithNumpyArray
    )


def test_strenum():
    """Test unstructure/structure round trip with strenum subclasses"""
    # Unstructured StrEnum is a string but not a StrEnum
    unstruct = converter.unstructure(Categories.one)
    assert isinstance(unstruct, str)
    assert not isinstance(unstruct, Categories)

    # StrEnum structured from string is a string and a StrEnum
    struct = converter.structure("two", Categories)
    assert isinstance(struct, str)
    assert isinstance(struct, Categories)
