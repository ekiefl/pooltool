from dataclasses import FrozenInstanceError

import numpy as np
import pytest

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

    # Unfortunately, this is allowed
    lin_seg.p1[0] = 10


def test_linear_segment_copy(lin_seg):
    copy = lin_seg.copy()

    # lin_seg and copy equate
    assert lin_seg is not copy
    assert lin_seg == copy

    # modifying lin_seg doesn't affect copy
    lin_seg.p1[0] = 10
    assert lin_seg != copy


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

    # Unfortunately, this is allowed
    circ_seg.center[0] = 10


def test_circular_segment_copy(circ_seg):
    copy = circ_seg.copy()

    # circ_seg and copy equate
    assert circ_seg is not copy
    assert circ_seg == copy

    # modifying circ_seg doesn't affect copy
    circ_seg.center[0] = 10
    assert circ_seg != copy


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


def test_pocket_frozen(pocket):
    # Cannot set attributes of frozen class
    with pytest.raises(FrozenInstanceError):
        pocket.center = np.array([10, 10, 10])

    # Unfortunately, this is allowed
    pocket.center[0] = 10


def test_pocket_copy(pocket):
    copy = pocket.copy()

    # pocket and copy equate
    assert pocket.contains is not copy.contains
    assert pocket is not copy
    assert pocket == copy

    # modifying pocket doesn't affect copy
    pocket.center[0] = 10
    assert pocket != copy


def test_cushion_segments_copy(lin_seg, circ_seg):
    segments = CushionSegments(
        linear={lin_seg.id: lin_seg}, circular={circ_seg.id: circ_seg}
    )
    copy = segments.copy()

    # segments and copy equate
    assert segments is not copy
    assert segments == copy

    # Their dictionaries are not the same
    assert segments.linear is not copy.linear
    assert segments.circular is not copy.circular
