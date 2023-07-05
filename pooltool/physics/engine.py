from __future__ import annotations

import attrs

from pooltool.physics.resolve import Resolver


@attrs.define
class PhysicsEngine:
    resolver: Resolver = attrs.field(factory=Resolver.default)
