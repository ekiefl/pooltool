"""Shared test helpers.

Plain functions (no pytest fixtures) that test modules import directly. Made
discoverable via ``pythonpath = ["tests"]`` in ``pyproject.toml``.
"""

from __future__ import annotations

import attrs

from pooltool.evolution.engine import SimulationEngine
from pooltool.physics.dimensionality import Dim
from pooltool.physics.resolve.resolver import Resolver


def patch_resolver_dims(resolver: Resolver, dim_value: Dim) -> None:
    """Set every resolver strategy's ``dim`` to ``dim_value``, in place."""
    for field in attrs.fields(type(resolver)):
        strategy = getattr(resolver, field.name)
        if hasattr(strategy, "dim"):
            strategy.dim = dim_value


def build_3d_engine(dim_value: Dim = Dim.THREE) -> SimulationEngine:
    """A ``SimulationEngine(is_3d=True)`` whose strategies are patched to ``dim_value``.

    Used by tests that need to exercise the 3D code path before real ``Dim.THREE``
    resolvers exist for every event type.

    TODO: This is a temporary measure. Drop the dim patching once every resolver
    slot has a ``Dim.THREE``-capable strategy (cushion + ball-ball; tracked by
    issues #308–#312). At that point this helper can be replaced by a direct
    ``SimulationEngine(is_3d=True)`` construction.
    """
    resolver = Resolver.default()
    patch_resolver_dims(resolver, dim_value)
    return SimulationEngine(resolver=resolver, is_3d=True)
