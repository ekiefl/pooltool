from __future__ import annotations

import filecmp
import tempfile
from pathlib import Path

import numpy as np
import pytest
from attrs import define
from numpy.typing import NDArray

from pooltool.serialize import (
    SerializeFormat,
    conversion,
    from_json,
    from_msgpack,
    to_json,
    to_msgpack,
)
from pooltool.utils.dataclasses import are_dataclasses_equal
from pooltool.utils.strenum import StrEnum, auto


@define
class ImNested:
    a: bool
    b: int
    c: str


@define
class SimpleObj:
    a: ImNested
    b: float
    c: set
    d: list


@define(eq=False)
class ComplexObj(SimpleObj):
    float64_array: NDArray[np.float64]
    float32_array: NDArray[np.float32]
    int32_array: NDArray[np.int32]
    an_enum: Categories

    def __eq__(self, other):
        return are_dataclasses_equal(self, other)


class Categories(StrEnum):
    one = auto()
    two = auto()
    three = auto()


@pytest.fixture
def simple_obj():
    """Contains only simple dtypes and attrs classes"""
    return SimpleObj(
        a=ImNested(a=True, b=42, c="foo"),
        b=47.0,
        c={1, 2, 3},
        d=[4, 3, 2, 1],
    )


@pytest.fixture
def complex_obj(simple_obj):
    return ComplexObj(
        a=simple_obj.a,
        b=simple_obj.b,
        c=simple_obj.c,
        d=simple_obj.d,
        float64_array=np.arange(9, dtype=np.float64).reshape((3, 3)),
        float32_array=np.arange(9, dtype=np.float32).reshape((3, 3)),
        int32_array=np.arange(9, dtype=np.int32).reshape((3, 3)),
        an_enum=Categories.three,
    )


# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fmt", [SerializeFormat.JSON, SerializeFormat.MSGPACK, SerializeFormat.YAML]
)
def test_round_python_trip_simple(simple_obj, fmt: SerializeFormat):
    """Round trip: structure -> unstructure -> structure"""
    c = conversion[fmt]
    assert c.structure(c.unstructure(simple_obj), SimpleObj) == simple_obj


@pytest.mark.parametrize("fmt", [SerializeFormat.JSON, SerializeFormat.MSGPACK])
def test_round_python_trip_complex(complex_obj, fmt: SerializeFormat):
    """Round trip: structure -> unstructure -> structure"""
    c = conversion[fmt]
    assert c.structure(c.unstructure(complex_obj), ComplexObj) == complex_obj


@pytest.mark.parametrize(
    "fmt", [SerializeFormat.JSON, SerializeFormat.MSGPACK, SerializeFormat.YAML]
)
def test_round_filesystem_trip_simple(simple_obj, fmt: SerializeFormat):
    """Round trip: structure -> unstructure -> filesystem -> unstructure -> structure"""

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / f"tmp.{fmt.ext}"

        # Write to file
        conversion.unstructure_to(simple_obj, path, fmt)

        # Read from file
        assert simple_obj == conversion.structure_from(path, SimpleObj, fmt)


@pytest.mark.parametrize("fmt", [SerializeFormat.JSON, SerializeFormat.MSGPACK])
def test_round_filesystem_trip_complex(complex_obj, fmt: SerializeFormat):
    """Round trip: structure -> unstructure -> filesystem -> unstructure -> structure"""

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / f"tmp.{fmt.ext}"

        # Write to file
        conversion.unstructure_to(complex_obj, path, fmt)

        # Read from file
        assert complex_obj == conversion.structure_from(path, ComplexObj, fmt)


def test_unstructure_json(complex_obj):
    c = conversion[SerializeFormat.JSON]
    uo = c.unstructure(complex_obj)

    # Arrays are nested lists
    assert isinstance(uo["float64_array"], list)
    assert isinstance(uo["float64_array"][0], list)
    assert isinstance(uo["float64_array"][0][0], float)

    assert isinstance(uo["float32_array"], list)
    assert isinstance(uo["float32_array"][0], list)
    assert isinstance(uo["float32_array"][0][0], float)

    assert isinstance(uo["int32_array"], list)
    assert isinstance(uo["int32_array"][0], list)
    assert isinstance(uo["int32_array"][0][0], int)

    # Enums are strs and not Enums
    assert isinstance(uo["an_enum"], str)
    assert not isinstance(uo["an_enum"], Categories)


def test_unstructure_to_json(complex_obj):
    fmt = SerializeFormat.JSON

    with tempfile.TemporaryDirectory() as tmp_dir:
        method_path = Path(tmp_dir) / f"method.{fmt.ext}"
        manual_path = Path(tmp_dir) / f"manual.{fmt.ext}"

        # Write with unstructure_to
        conversion.unstructure_to(complex_obj, method_path, fmt)

        # Write manually
        uo = conversion[fmt].unstructure(complex_obj)
        to_json(uo, manual_path)

        # Files are equal
        assert filecmp.cmp(method_path, manual_path, shallow=False)


def test_structure_json(complex_obj):
    c = conversion[SerializeFormat.JSON]
    uo = c.unstructure(complex_obj)
    o = c.structure(uo, ComplexObj)

    # Array types are persistent
    assert o.float64_array.dtype == np.float64
    assert o.float32_array.dtype == np.float32
    assert o.int32_array.dtype == np.int32

    # Enums are Enums
    assert isinstance(o.an_enum, Categories)


def test_structure_from_json(complex_obj):
    fmt = SerializeFormat.JSON

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / f"method.{fmt.ext}"
        conversion.unstructure_to(complex_obj, path, fmt)

        # Read with structure_from
        output = conversion.structure_from(path, ComplexObj, fmt)

        # Read manually
        output_manual = conversion[fmt].structure(from_json(path), ComplexObj)

    assert output == output_manual

    # Array types are persistent
    assert output.float64_array.dtype == np.float64
    assert output.float32_array.dtype == np.float32
    assert output.int32_array.dtype == np.int32

    # Enums are Enums
    assert isinstance(output.an_enum, Categories)


def test_unstructure_msgpack(complex_obj):
    c = conversion[SerializeFormat.MSGPACK]
    uo = c.unstructure(complex_obj)

    # Arrays are kept as arrays
    assert isinstance(uo["float64_array"], np.ndarray)
    assert isinstance(uo["float32_array"], np.ndarray)
    assert isinstance(uo["int32_array"], np.ndarray)

    # Not only that, but they are the same object
    assert uo["float64_array"] is complex_obj.float64_array
    assert uo["float32_array"] is complex_obj.float32_array
    assert uo["int32_array"] is complex_obj.int32_array

    # Enums are strs and not Enums
    assert isinstance(uo["an_enum"], str)
    assert not isinstance(uo["an_enum"], Categories)


def test_unstructure_to_msgpack(complex_obj):
    fmt = SerializeFormat.MSGPACK

    with tempfile.TemporaryDirectory() as tmp_dir:
        method_path = Path(tmp_dir) / f"method.{fmt.ext}"
        manual_path = Path(tmp_dir) / f"manual.{fmt.ext}"

        # Write with unstructure_to
        conversion.unstructure_to(complex_obj, method_path, fmt)

        # Write manually
        uo = conversion[fmt].unstructure(complex_obj)
        to_msgpack(uo, manual_path)

        # Files are equal
        assert filecmp.cmp(method_path, manual_path, shallow=False)


def test_structure_msgpack(complex_obj):
    c = conversion[SerializeFormat.MSGPACK]
    uo = c.unstructure(complex_obj)
    o = c.structure(uo, ComplexObj)

    # Array types are persistent
    assert o.float64_array.dtype == np.float64
    assert o.float32_array.dtype == np.float32
    assert o.int32_array.dtype == np.int32

    # Enums are Enums
    assert isinstance(o.an_enum, Categories)


def test_structure_from_msgpack(complex_obj):
    fmt = SerializeFormat.MSGPACK

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / f"method.{fmt.ext}"
        conversion.unstructure_to(complex_obj, path, fmt)

        # Read with structure_from
        output = conversion.structure_from(path, ComplexObj, fmt)

        # Read manually
        output_manual = conversion[fmt].structure(from_msgpack(path), ComplexObj)

    assert output == output_manual

    # Array types are persistent
    assert output.float64_array.dtype == np.float64
    assert output.float32_array.dtype == np.float32
    assert output.int32_array.dtype == np.int32

    # Enums are Enums
    assert isinstance(output.an_enum, Categories)
