from __future__ import annotations

import attrs

from pooltool.physics.resolve import Resolver


@attrs.define
class PhysicsEngine:
    """A billiards physics engine

    This object """
    resolver: Resolver = attrs.field(factory=Resolver.default)
