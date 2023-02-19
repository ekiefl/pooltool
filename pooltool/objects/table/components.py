"""A module housing all of the components that make up a table (pockets, cushions, etc)"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Dict

import numpy as np
from numpy.typing import NDArray

import pooltool.utils as utils


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


@dataclass
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
        self.p1 = np.array(self.p1, dtype=np.float64)
        self.p2 = np.array(self.p2, dtype=np.float64)

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


@dataclass
class CircularCushionSegment:
    """A circular cushion segment defined a circle center and radius

    Attributes:
        center:
            A length-3 array that defines a 3D point in space of the circle center.
            starts. The last component (z-axis) is the height of the cushion segment.
        radius:
            The radius of the circular cushion segment.
    """

    id: str
    center: NDArray[np.float64]
    radius: float

    @property
    def height(self):
        return self.center[2]

    @property
    def a(self):
        return self.center[0]

    @property
    def b(self):
        return self.center[1]

    def get_normal(self, rvw):
        normal = utils.unit_vector_fast(rvw[0, :] - self.center)
        normal[2] = 0  # remove z-component
        return normal


@dataclass
class CushionSegments:
    linear: Dict[str, LinearCushionSegment]
    circular: Dict[str, CircularCushionSegment]


@dataclass
class Pocket:
    id: str
    center: NDArray[np.float64]
    radius: float
    depth: float = field(default=0.08)
    contains: set = field(default_factory=set)

    @property
    def a(self):
        return self.center[0]

    @property
    def b(self):
        return self.center[1]

    def add(self, ball_id):
        self.contains.add(ball_id)

    def remove(self, ball_id):
        self.contains.remove(ball_id)
