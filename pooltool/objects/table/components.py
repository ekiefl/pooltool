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

    Important for constructing cushions if simulation performance speed is required.

    For most table geometries, the playing surface only exists on one side of the
    cushion, so collisions only need to be checked for one direction. This direction can
    be specified with this class's attributes.

    Attributes:
        SIDE1: Use side 1.
        SIDE2: Use side 2.
        BOTH: Use sides 1 and 2.

    Unfortunately, the rule governing whether to use :attr:`SIDE1` or :attr:`SIDE2` is
    not clear and instead requires experimentation.

    If :attr:`BOTH` is used, both collision checks are performed which makes collision
    checks twice as slow.

    Note:
        This used to inherit from ``Enum``, but accessing the cushion direction in
        ``get_next_ball_linear_cushion_collision`` somehow took up 20% of the functions
        runtime so I removed it.
    """

    SIDE1 = 0
    SIDE2 = 1
    BOTH = 2


@define(eq=False, frozen=True, slots=False)
class LinearCushionSegment:
    """A linear cushion segment defined by the line between points p1 and p2

    Attributes:
        id:
            The ID of the cushion segment.
        p1:
            The 3D coordinate where the cushion segment starts.

            Note:
                - p1 and p2 must share the same height (``p1[2] == p2[2]``).
        p2:
            The 3D coordinate where the cushion segment ends.

            Note:
                - p1 and p2 must share the same height (``p1[2] == p2[2]``).
        direction:
            The cushion direction (*default* = :attr:`CushionDirection.BOTH`).

            See :class:`CushionDirection` for explanation.
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
        """The height of the cushion

        .. cached_property_note::
        """
        return self.p1[2]

    @cached_property
    def lx(self) -> float:
        """The x-coefficient (:math:`l_x`) of the cushion's 2D general form line equation

        .. cached_property_note::

        The cushion's general form line equation in the :math:`XY` plane (*i.e.*
        dismissing the z-component) is

        .. math:: 

            l_x x + l_y y + l_0 = 0

        where 

        .. math::

            \\begin{align*}
            l_x &= -\\frac{p_{2y} - p_{1y}}{p_{2x} - p_{1x}} \\\\
            l_y &= 1 \\\\
            l_0 &= \\frac{p_{2y} - p_{1y}}{p_{2x} - p_{1x}} p_{1x} - p_{1y} \\\\
            \\end{align*}
        """
        p1x, p1y, _ = self.p1
        p2x, p2y, _ = self.p2
        return 1 if (p2x - p1x) == 0 else -(p2y - p1y) / (p2x - p1x)

    @cached_property
    def ly(self) -> float:
        """The x-coefficient (:math:`l_y`) of the cushion's 2D general form line equation

        See :meth:`lx` for definition.

        .. cached_property_note::
        """
        return 0 if (self.p2[0] - self.p1[0]) == 0 else 1

    @cached_property
    def l0(self) -> float:
        """The constant term (:math:`l_0`) of the cushion's 2D general form line equation

        See :meth:`lx` for definition.

        .. cached_property_note::
        """
        p1x, p1y, _ = self.p1
        p2x, p2y, _ = self.p2
        return -p1x if (p2x - p1x) == 0 else (p2y - p1y) / (p2x - p1x) * p1x - p1y

    @cached_property
    def normal(self) -> NDArray[np.float64]:
        """The line's normal vector, with the z-component set to 0.

        Warning:
            The returned normal vector is arbitrarily directed, meaning it may point
            away from the table surface, rather than towards it. This nonideality is
            properly handled in downstream simulation logic, however if you're using
            this method for custom purposes, you may want to reverse the direction of
            this vector by negating it.
        """
        return ptmath.unit_vector(np.array([self.lx, self.ly, 0]))

    def get_normal(self, rvw: NDArray[np.float64]) -> NDArray[np.float64]:
        """Calculates the normal vector

        Warning:
            The returned normal vector is arbitrarily directed, meaning it may point
            away from the table surface, rather than towards it. This nonideality is
            properly handled in downstream simulation logic, however if you're using
            this method for custom purposes, you may want to reverse the direction of
            this vector by negating it.

        Args:
            rvw:
                The kinematic state vectors of the contacting balls.

                See ``rvw`` parameter of :class:`pooltool.objects.ball.datatypes.BallState`.

        Returns:
            NDArray[np.float64]:
                The line's normal vector, with the z-component set to 0.

        Note:
            - This method only exists for call signature parity with
              :meth:`CircularCushionSegment.get_normal`. Consider using :meth:`normal`
              instead.
        """
        return self.normal

    def copy(self) -> LinearCushionSegment:
        """Create a copy"""
        # LinearCushionSegment is a frozen instance, and its attributes are either (a)
        # immutable, or (b) have read-only flags set. It is sufficient to simply return
        # oneself.
        return self

    @staticmethod
    def dummy() -> LinearCushionSegment:
        return LinearCushionSegment(
            id="dummy", p1=np.array([0, 0, 1]), p2=np.array([1, 1, 1])
        )


@define(frozen=True, eq=False, slots=False)
class CircularCushionSegment:
    """A circular cushion segment defined by a circle center and radius

    Attributes:
        id:
            The ID of the cushion segment.
        center:
            A length-3 array specifying the circular cushion's center.

            ``center[0]``, ``center[1]``, and ``center[2]`` are the x-, y-, and
            z-coordinates of the cushion's center. The circle is assumed to be parallel to
            the XY plane, which makes ``center[2]`` is the height of the cushion.
        radius:
            The radius of the cushion segment.
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
        """The height of the cushion

        .. cached_property_note::
        """
        return self.center[2]

    @cached_property
    def a(self) -> float:
        """The x-coordinate of the cushion's center

        .. cached_property_note::
        """
        return self.center[0]

    @cached_property
    def b(self) -> float:
        """The y-coordinate of the cushion's center

        .. cached_property_note::
        """
        return self.center[1]

    def get_normal(self, rvw: NDArray[np.float64]) -> NDArray[np.float64]:
        """Calculates the normal vector for a ball contacting the cushion

        Assumes that the ball is in fact in contact with the cushion.

        Args:
            rvw: The kinematic state vectors of the contacting ball (see
            :attr:`pooltool.objects.ball.datatypes.BallState.rvw`).

        Returns:
            NDArray[np.float64]:
                The normal vector, with the z-component set to 0.
        """
        normal = rvw[0, :] - self.center
        normal[2] = 0  # remove z-component
        return ptmath.unit_vector(normal)

    def copy(self) -> CircularCushionSegment:
        """Create a copy"""
        # CircularCushionSegment is a frozen instance, and its attributes are either (a)
        # immutable, or (b) have read-only flags set. It is sufficient to simply return
        # oneself.
        return self

    @staticmethod
    def dummy() -> CircularCushionSegment:
        return CircularCushionSegment(
            id="dummy", center=np.array([0, 0, 0], dtype=np.float64), radius=10.0
        )


CushionSegment = Union[LinearCushionSegment, CircularCushionSegment]


@define
class CushionSegments:
    """A collection of cushion segments

    Cushion segments can be either linear (see :class:`LinearCushionSegment`) or
    circular (see :class:`CircularCushionSegment`). This class stores both.

    Attributes:
        linear:
            A dictionary of linear cushion segments.

            Warning:
                Keys must match the value IDs, *e.g.* ``{"2":
                LinearCushionSegment(id="2", ...)}``
        circular:
            A dictionary of circular cushion segments.

            Warning:
                Keys must match the value IDs, *e.g.* ``{"2t":
                CircularCushionSegment(id="2t", ...)}``
    """

    linear: Dict[str, LinearCushionSegment] = field()
    circular: Dict[str, CircularCushionSegment] = field()

    @linear.validator  # type: ignore
    @circular.validator  # type: ignore
    def _keys_match_value_ids(self, _, attribute) -> None:
        for key, val in attribute.items():
            assert key == val.id, f"Key '{key}' mismatch with ID '{val.id}'"

    def copy(self) -> CushionSegments:
        """Create a copy"""
        # Delegates the deep-ish copying of LinearCushionSegment and
        # CircularCushionSegment elements to their respective copy() methods. Uses
        # dictionary comprehensions to construct equal but different `linear` and
        # `circular` attributes.
        return evolve(
            self,
            linear={k: v.copy() for k, v in self.linear.items()},
            circular={k: v.copy() for k, v in self.circular.items()},
        )


@define(eq=False, frozen=True, slots=False)
class Pocket:
    """A circular pocket

    Attributes:
        id:
            The ID of the pocket.
        center:
            A length-3 array specifying the pocket's position.

            - ``center[0]`` is the x-coordinate of the pocket's center
            - ``center[1]`` is the y-coordinate of the pocket's center
            - ``center[2]`` must be 0.0
        radius:
            The radius of the pocket.
        depth:
            How deep the pocket is.
        contains:
            Stores the ball IDs of pocketed balls (*default* = ``set()``).
    """

    id: str
    center: NDArray[np.float64]
    radius: float
    depth: float = field(default=0.08)
    contains: set = field(factory=set)

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

        .. cached_property_note::
        """
        return self.center[0]

    @cached_property
    def b(self) -> float:
        """The y-coordinate of the pocket's center

        .. cached_property_note::
        """
        return self.center[1]

    def add(self, ball_id: str) -> None:
        """Add a ball ID to :attr:`contains`"""
        self.contains.add(ball_id)

    def remove(self, ball_id: str) -> None:
        """Remove a ball ID from :attr:`contains`"""
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
