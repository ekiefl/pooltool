"""Houses all components that make up a table (pockets, cushions, etc)"""

from __future__ import annotations

import copy
import enum
from dataclasses import dataclass, field, replace
from typing import Dict, Union

import numpy as np
from numpy.typing import NDArray

import pooltool.utils as utils
from pooltool.utils.dataclasses import are_dataclasses_equal


class CushionDirection(enum.Enum):
    """An Enum for the direction of a cushion

    For most table geometries, the playing surface only exists on one side of the
    cushion, so collisions only need to be checked for one direction. This direction can
    be specified with the CushionDirection Enum. To determine whether 0 or 1 should be
    used, please experiment (FIXME: determine the rule, it is not straightforward like
    "left or right of the vector from p1 to p2"). By default, both collision directions
    are checked, which can be specified explicitly by passing 2, however this makes
    collision checks twice as slow for event-based shot evolution algorithms.
    """

    SIDE1 = 0
    SIDE2 = 1
    BOTH = 2


@dataclass(eq=False, frozen=True)
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
    direction: CushionDirection = field(default=CushionDirection.BOTH)

    def __post_init__(self):
        # Segment must have constant height
        assert self.p1[2] == self.p2[2]

        # p1 and p2 are read only
        self.p1.flags["WRITEABLE"] = False
        self.p2.flags["WRITEABLE"] = False

    def __eq__(self, other):
        return are_dataclasses_equal(self, other)

    @property
    def height(self):
        return self.p1[2]

    @property
    def lx(self):
        p1x, p1y, _ = self.p1
        p2x, p2y, _ = self.p2
        return 1 if (p2x - p1x) == 0 else -(p2y - p1y) / (p2x - p1x)

    @property
    def ly(self):
        return 0 if (self.p2[0] - self.p1[0]) == 0 else 1

    @property
    def l0(self):
        p1x, p1y, _ = self.p1
        p2x, p2y, _ = self.p2
        return -p1x if (p2x - p1x) == 0 else (p2y - p1y) / (p2x - p1x) * p1x - p1y

    @property
    def normal(self):
        return utils.unit_vector_fast(np.array([self.lx, self.ly, 0]))

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


@dataclass(frozen=True, eq=False)
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

    def __post_init__(self):
        assert len(self.center) == 3

        # center is read only
        self.center.flags["WRITEABLE"] = False

    @property
    def height(self) -> float:
        return self.center[2]

    @property
    def a(self) -> float:
        return self.center[0]

    @property
    def b(self) -> float:
        return self.center[1]

    def get_normal(self, rvw) -> NDArray[np.float64]:
        normal = utils.unit_vector_fast(rvw[0, :] - self.center)
        normal[2] = 0  # remove z-component
        return normal

    def copy(self) -> CircularCushionSegment:
        """Create a deep-ish copy

        CircularCushionSegment is a frozen instance, and its attributes are either (a)
        immutable, or (b) have read-only flags set. It is sufficient to simply return
        oneself.
        """
        return self

    @staticmethod
    def dummy() -> CircularCushionSegment:
        return CircularCushionSegment(id="dummy", center=np.array([0, 0, 0]), radius=10)


CushionSegment = Union[LinearCushionSegment, CircularCushionSegment]


@dataclass
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
        return replace(
            self,
            linear={k: v.copy() for k, v in self.linear.items()},
            circular={k: v.copy() for k, v in self.circular.items()},
        )


@dataclass(eq=False, frozen=True)
class Pocket:
    id: str
    center: NDArray[np.float64]
    radius: float
    depth: float = field(default=0.08)
    contains: set = field(default_factory=set)

    def __post_init__(self):
        assert len(self.center) == 3
        assert self.center[2] == 0

        # center is read only
        self.center.flags["WRITEABLE"] = False

    def __eq__(self, other):
        return are_dataclasses_equal(self, other)

    @property
    def a(self) -> float:
        return self.center[0]

    @property
    def b(self) -> float:
        return self.center[1]

    @property
    def potting_point(self) -> NDArray[np.float64]:
        """The 2D coordinates that should be aimed at for the ball to be sunk

        Determines the coordinates of a point ahead of the pocket where, if a traveling
        ball were to pass through it, would result in the ball being sunk. The point
        would be a radius to left/right, and a radius up/down, depending on the pocket.
        These values were determined empirically by trial and error.
        """
        (x, y, _), r = self.center, self.radius

        if self.id[0] == "l":
            x = x + r
        else:
            x = x - r

        if self.id[1] == "b":
            y = y + r
        elif self.id[1] == "t":
            y = y - r

        return np.array([x, y], dtype=np.float64)

    def add(self, ball_id: str) -> None:
        self.contains.add(ball_id)

    def remove(self, ball_id: str) -> None:
        self.contains.remove(ball_id)

    def copy(self) -> Pocket:
        """Create a deep-ish copy

        Pocket is a frozen instance, and except for `contains`, its attributes are
        either (a) immutable, or (b) have read-only flags set. Therefore, only a copy of
        `contains` needs to be made. Since it's members are strs (immutable), a shallow
        copy suffices.
        """
        return replace(self, contains=copy.copy(self.contains))

    @staticmethod
    def dummy() -> Pocket:
        return Pocket(id="dummy", center=np.array([0, 0, 0]), radius=10)
