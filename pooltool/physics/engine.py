"""The physics engine of pooltool"""

from __future__ import annotations

import attrs

from pooltool.physics.resolve import Resolver


@attrs.define
class PhysicsEngine:
    """A billiards engine for pluggable physics.

    Important:
        Currently, only event resolution is a part of this class. The sliding, rolling,
        and spinning ball trajectory evolution is currently "hard-coded", however can in
        theory be added to this class to enable alternative trajectory models.

    Attributes:
        resolver:
            The physics engine responsible for resolving events.
    """

    resolver: Resolver = attrs.field(factory=Resolver.default)


__all__ = [
    "PhysicsEngine",
]
