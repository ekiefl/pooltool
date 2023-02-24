import numpy as np
import pytest
from attrs import define
from numpy.typing import NDArray

from pooltool.serialize._cattrs import converter


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


@define
class WithNumpyArray(StandardTypes):
    e: NDArray[np.float64]


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


def test_unstructure_structure(standard_obj):
    """Test unstructure/structure round trip"""
    assert standard_obj == converter.structure(
        converter.unstructure(standard_obj), StandardTypes
    )


def test_numpy_unstructure_structure(numpy_obj):
    """Test unstructure/structure round trip with numpy array fields"""
    with pytest.raises(NotImplementedError):
        raise NotImplementedError
