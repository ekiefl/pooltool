import numpy as np
import pytest
from attrs.exceptions import FrozenInstanceError

from pooltool.objects.table.components import (
    CircularCushionSegment,
    CushionSegments,
    LinearCushionSegment,
    Pocket,
)


@pytest.fixture
def lin_seg():
    return LinearCushionSegment(
        "lt",
        p1=np.array([0, 0, 0]),
        p2=np.array([1, 1, 0]),
    )


@pytest.fixture
def circ_seg():
    return CircularCushionSegment(
        "circ",
        center=np.array([0, 0, 0]),
        radius=1,
    )


@pytest.fixture
def pocket():
    return Pocket(
        "pocket",
        center=np.array([0, 0, 0]),
        radius=1,
    )


def test_linear_segment_creation():
    # Cannot create linear segment with different endpoint heights
    with pytest.raises(AssertionError):
        LinearCushionSegment(
            "lt",
            p1=np.array([0, 0, 0]),
            p2=np.array([0, 0, 1]),
        )


def test_linear_segment_frozen(lin_seg):
    # Cannot set attributes of frozen class
    with pytest.raises(FrozenInstanceError):
        lin_seg.p1 = np.array([10, 10, 10])

    # Cannot even modify array elements
    with pytest.raises(ValueError, match="assignment destination is read-only"):
        lin_seg.p1[0] = 10

    # Not bulletproof though. One can set the WRITABLE flag
    lin_seg.p1.flags["WRITEABLE"] = True
    lin_seg.p1[0] = 10


def test_linear_segment_copy(lin_seg):
    copy = lin_seg.copy()

    # lin_seg and copy equate
    assert lin_seg == copy

    # In fact, lin_seg and copy are the same object. We can get away with this because
    # it's a frozen object with either (a) immutable attributes or (b) attributes which
    # with read-only flags set
    assert lin_seg is copy


def test_circular_segment_creation():
    # center array is length three
    with pytest.raises(AssertionError):
        CircularCushionSegment(
            "circ",
            center=np.array([0, 0]),
            radius=1,
        )


def test_circular_segment_frozen(circ_seg):
    # Cannot set attributes of frozen class
    with pytest.raises(FrozenInstanceError):
        circ_seg.center = np.array([10, 10, 10])

    # Cannot even modify array elements
    with pytest.raises(ValueError, match="assignment destination is read-only"):
        circ_seg.center[0] = 10

    # Not bulletproof though. One can set the WRITABLE flag
    circ_seg.center.flags["WRITEABLE"] = True
    circ_seg.center[0] = 10


def test_circular_segment_copy(circ_seg):
    copy = circ_seg.copy()

    # circ_seg and copy equate
    assert circ_seg == copy

    # In fact, circ_seg and copy are the same object. We can get away with this because
    # it's a frozen object with either (a) immutable attributes or (b) attributes which
    # with read-only flags set
    assert circ_seg is copy


def test_pocket_creation():
    # center array is length three
    with pytest.raises(AssertionError):
        Pocket(
            "pocket",
            center=np.array([0, 0]),
            radius=1,
        )

    # Third component must be 0 (z=0)
    with pytest.raises(AssertionError):
        Pocket(
            "pocket",
            center=np.array([0, 0, 3]),
            radius=1,
        )

    # That's better
    Pocket(
        "pocket",
        center=np.array([0, 0, 0]),
        radius=1,
    )


def test_pocket_modifiability(pocket):
    """Test what is and isn't modifiable for Pocket"""
    # Cannot set attributes of frozen class
    with pytest.raises(FrozenInstanceError):
        pocket.center = np.array([10, 10, 10])
    with pytest.raises(FrozenInstanceError):
        pocket.contains = set()

    # Cannot modify array elements
    with pytest.raises(ValueError, match="assignment destination is read-only"):
        pocket.center[0] = 10

    # Not bulletproof though. One can set the WRITABLE flag
    pocket.center.flags["WRITEABLE"] = True
    pocket.center[0] = 10

    # One can however, add and subtract from `contains`
    pocket.contains.add("dummy")


def test_pocket_copy(pocket):
    copy = pocket.copy()

    # pocket and copy equate
    assert pocket == copy

    # center is read only, so its safe that they share the same reference
    pocket.center is copy.center  # type: ignore

    # contains is mutable, so separate objects is necessary
    assert pocket.contains == copy.contains
    assert pocket.contains is not copy.contains


def test_cushion_segments_copy(lin_seg, circ_seg):
    segments = CushionSegments(
        linear={lin_seg.id: lin_seg}, circular={circ_seg.id: circ_seg}
    )
    copy = segments.copy()

    # segments and copy equate
    assert segments == copy

    # Their dictionaries are not the same
    assert segments.linear is not copy.linear
    assert segments.circular is not copy.circular

    # You can't change the elements within a dictionary
    with pytest.raises(ValueError, match="assignment destination is read-only"):
        segments.linear[lin_seg.id].p1[0] = 4

    # But you can add new elements to `copy` without changing `segments`
    copy.linear["new"] = circ_seg
    assert "new" not in segments.linear


def test_cushion_segments_id_clash(lin_seg, circ_seg):
    # No problem
    CushionSegments(linear={lin_seg.id: lin_seg}, circular={circ_seg.id: circ_seg})

    # Keys don't match value IDs
    with pytest.raises(AssertionError):
        CushionSegments(linear={"wrong": lin_seg}, circular={circ_seg.id: circ_seg})
    with pytest.raises(AssertionError):
        CushionSegments(linear={lin_seg.id: lin_seg}, circular={"wrong": circ_seg})
    with pytest.raises(AssertionError):
        CushionSegments(linear={":(": lin_seg}, circular={"wrong": circ_seg})
