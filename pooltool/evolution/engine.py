"""The simulation engine of pooltool"""

from __future__ import annotations

import attrs

from pooltool.evolution.event_based.detect import EventDetector
from pooltool.physics.dimensionality import Dim
from pooltool.physics.resolve import Resolver


@attrs.define
class SimulationEngine:
    """A pluggable bundle of strategies used by the simulator.

    Holds the strategies that define how a simulation is carried out: how events are
    detected and how they are resolved. The simulator is handed an instance of this
    class and routes work to its components.

    Attributes:
        resolver:
            The strategy responsible for resolving events.
        detector:
            The strategy responsible for detecting the next event.
        is_3d:
            Whether the simulation supports the airborne motion state and ball-table
            events. Validated at construction against the dimensionality capability
            (``dim``) of every bundled strategy in ``resolver`` and ``detector``.
    """

    resolver: Resolver = attrs.field(factory=Resolver.default)
    detector: EventDetector = attrs.field(factory=EventDetector.default)
    is_3d: bool = False

    def __attrs_post_init__(self) -> None:
        required = Dim.THREE if self.is_3d else Dim.TWO
        for bundle in (self.resolver, self.detector):
            for field in attrs.fields(type(bundle)):
                strategy = getattr(bundle, field.name)
                if not attrs.has(type(strategy)):
                    continue
                if not hasattr(strategy, "dim"):
                    raise AttributeError(
                        f"{type(bundle).__name__}.{field.name} "
                        f"({type(strategy).__name__}) is missing required "
                        f"'dim' attribute"
                    )
                if strategy.dim not in (required, Dim.BOTH):
                    raise ValueError(
                        f"{type(bundle).__name__}.{field.name} "
                        f"({type(strategy).__name__}) has dim={strategy.dim}, "
                        f"incompatible with is_3d={self.is_3d}; "
                        f"expected {required} or {Dim.BOTH}"
                    )


__all__ = [
    "SimulationEngine",
]
