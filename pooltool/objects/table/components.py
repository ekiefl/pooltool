"""Houses all components that make up a table (pockets, cushions, etc)"""

from __future__ import annotations

import copy
from functools import cached_property
from typing import Dict, Union

import numpy as np
from attrs import define, evolve, field
from numpy.typing import NDArray

import pooltool.ptmath as ptmath
from pooltool.utils.dataclasses import are_dataclasses_equal


class CushionDirection:
    """An Enum for the direction of a cushion

    For most table geometries, the playing surface only exists on one side of the
    cushion, so collisions only need to be checked for one direction. This direction can
    be specified with the CushionDirection Enum. To determine whether 0 or 1 should be
    used, please experiment (FIXME: determine the rule, it is not straightforward like
    "left or right of the vector from p1 to p2"). By default, both collision directions
    are checked, which can be specified explicitly by passing 2, however this makes
    collision checks twice as slow for event-based shot evolution algorithms.

    NOTE: This used to be an Enum, but accessing the cushion direction in
    `get_next_ball_linear_cushion_collision` somehow took up 20% of the functions
    runtime so I removed it.
    """

    SIDE1 = 0
    SIDE2 = 1
    BOTH = 2


@define(eq=False, frozen=True, slots=False)
class LinearCushionSegment:
    """A linear cushion segment defined by the line between points p1 and p2

    Attributes:
        p1:
            A length-3 array that defines a 3D point in space where the cushion segment
            starts.
        p2:
            A length-3 array that defines a 3D point in space where the cushion segment
            ends.
    """

    id: str
    p1: NDArray[np.float64]
    p2: NDArray[np.float64]
    direction: int = field(default=CushionDirection.BOTH)

    def __attrs_post_init__(self):
        # Segment must have constant height
        assert self.p1[2] == self.p2[2]

        # p1 and p2 are read only
        self.p1.flags["WRITEABLE"] = False
        self.p2.flags["WRITEABLE"] = False

    def __eq__(self, other):
        return are_dataclasses_equal(self, other)

    @cached_property
    def height(self) -> float:
        return self.p1[2]

    @cached_property
    def lx(self) -> float:
        p1x, p1y, _ = self.p1
        p2x, p2y, _ = self.p2
        return 1 if (p2x - p1x) == 0 else -(p2y - p1y) / (p2x - p1x)

    @cached_property
    def ly(self) -> float:
        return 0 if (self.p2[0] - self.p1[0]) == 0 else 1

    @cached_property
    def l0(self) -> float:
        p1x, p1y, _ = self.p1
        p2x, p2y, _ = self.p2
        return -p1x if (p2x - p1x) == 0 else (p2y - p1y) / (p2x - p1x) * p1x - p1y

    @cached_property
    def normal(self):
        return ptmath.unit_vector(np.array([self.lx, self.ly, 0]))

    def get_normal(self, rvw):
        return self.normal

    def copy(self):
        """Create a deep-ish copy

        LinearCushionSegment is a frozen instance, and its attributes are either (a)
        immutable, or (b) have read-only flags set. It is sufficient to simply return
        oneself.
        """
        return self

    @staticmethod
    def dummy() -> LinearCushionSegment:
        return LinearCushionSegment(
            id="dummy", p1=np.array([0, 0, 1]), p2=np.array([1, 1, 1])
        )


@define(frozen=True, eq=False, slots=False)
class CircularCushionSegment:
    """A circular cushion segment defined a circle center and radius

    Attributes:
        center:
            A length-3 tuple that defines a 3D point in space of the circle center.
            starts. The last component (z-axis) is the height of the cushion segment.
        radius:
            The radius of the circular cushion segment.
    """

    id: str
    center: NDArray[np.float64]
    radius: float

    def __eq__(self, other):
        return are_dataclasses_equal(self, other)

    def __attrs_post_init__(self):
        assert len(self.center) == 3

        # center is read only
        self.center.flags["WRITEABLE"] = False

    @cached_property
    def height(self) -> float:
        return self.center[2]

    @cached_property
    def a(self) -> float:
        return self.center[0]

    @cached_property
    def b(self) -> float:
        return self.center[1]

    def get_normal(self, rvw) -> NDArray[np.float64]:
        normal = rvw[0, :] - self.center
        normal[2] = 0  # remove z-component
        return ptmath.unit_vector(normal)

    def copy(self) -> CircularCushionSegment:
        """Create a deep-ish copy

        CircularCushionSegment is a frozen instance, and its attributes are either (a)
        immutable, or (b) have read-only flags set. It is sufficient to simply return
        oneself.
        """
        return self

    @staticmethod
    def dummy() -> CircularCushionSegment:
        return CircularCushionSegment(
            id="dummy", center=np.array([0, 0, 0], dtype=np.float64), radius=10.0
        )


CushionSegment = Union[LinearCushionSegment, CircularCushionSegment]


@define
class CushionSegments:
    linear: Dict[str, LinearCushionSegment]
    circular: Dict[str, CircularCushionSegment]

    def copy(self) -> CushionSegments:
        """Create a deep-ish copy

        Delegates the deep-ish copying of LinearCushionSegment and
        CircularCushionSegment elements to their respective copy() methods. Uses
        dictionary comprehensions to construct equal but different `linear` and
        `circular` attributes.
        """
        return evolve(
            self,
            linear={k: v.copy() for k, v in self.linear.items()},
            circular={k: v.copy() for k, v in self.circular.items()},
        )


@define(eq=False, frozen=True, slots=False)
class Pocket:
    """A circular pocket"""
    id: str
    """The ID of the pocket (*required*)"""
    center: NDArray[np.float64]
    """A length-3 array specifying the pocket's position (*required*)

    - ``center[0]`` is the x-coordinate of the pocket's center
    - ``center[1]`` is the y-coordinate of the pocket's center
    - ``center[2]`` must be 0.0
    """
    radius: float
    """The radius of the pocket (*required*)"""
    depth: float = field(default=0.08)
    """How deep the pocket is (*default* = 0.08)"""
    contains: set = field(factory=set)
    """Stores the ball IDs of pocketed balls (*default* = ``set()``)"""

    def __attrs_post_init__(self):
        assert len(self.center) == 3
        assert self.center[2] == 0

        # center is read only
        self.center.flags["WRITEABLE"] = False

    def __eq__(self, other):
        return are_dataclasses_equal(self, other)

    @cached_property
    def a(self) -> float:
        """The x-coordinate of the pocket's center

        Note:
            This is a (cached) property, call it like ``pocket.a``, not ``pocket.a()``.
        """
        return self.center[0]

    @cached_property
    def b(self) -> float:
        """The y-coordinate of the pocket's center

        Note:
            This is a (cached) property, call it like ``pocket.b``, not ``pocket.b()``.
        """
        return self.center[1]

    def add(self, ball_id: str) -> None:
        """Add a ball ID to :attr:`contains`"""
        self.contains.add(ball_id)

    def remove(self, ball_id: str) -> None:
        """Remove a ball ID to :attr:`contains`"""
        self.contains.remove(ball_id)

    def copy(self) -> Pocket:
        """Create a copy"""
        # Pocket is a frozen instance, and except for `contains`, its attributes are
        # either (a) immutable, or (b) have read-only flags set. Therefore, only a copy
        # of `contains` needs to be made. Since it's members are strs (immutable), a
        # shallow copy suffices.
        return evolve(self, contains=copy.copy(self.contains))

    @staticmethod
    def dummy() -> Pocket:
        return Pocket(id="dummy", center=np.array([0, 0, 0]), radius=10)
