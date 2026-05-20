"""The simulation engine of pooltool"""

from __future__ import annotations

import attrs

from pooltool.evolution.event_based.detect import EventDetector
from pooltool.physics.dimensionality import SKIP_DIMENSION, Dim
from pooltool.physics.resolve import Resolver


@attrs.define
class SimulationEngine:
    """A bundle of physics strategies used by the simulator.

    Holds the resolver (pluggable per-event-type collision strategies) and the detector.
    The simulator is handed an instance and routes work to its components.

    Attributes:
        is_3d:
            Whether the simulation supports the airborne motion state and
            ball-table events. Validated at construction against the
            dimensionality capability (``dim``) of every bundled strategy in
            ``resolver``.
        resolver:
            Pluggable bundle of event-resolution strategies. Each strategy
            declares a ``Dim`` capability (except ``ball_table``).
        detector:
            Canonical event detector. Not constructor-passable — built from
            ``is_3d`` automatically.
    """

    is_3d: bool = False
    resolver: Resolver = attrs.field(factory=Resolver.default)
    detector: EventDetector = attrs.field(init=False)

    @detector.default  # type: ignore
    def _default_detector(self) -> EventDetector:
        return EventDetector(is_3d=self.is_3d)

    def __attrs_post_init__(self) -> None:
        self._validate_dimensionality()

    def _validate_dimensionality(self) -> None:
        required = Dim.THREE if self.is_3d else Dim.TWO

        for field in attrs.fields(type(self.resolver)):
            if field.name in SKIP_DIMENSION:
                continue
            strategy = getattr(self.resolver, field.name)
            if not attrs.has(type(strategy)):
                continue
            if not hasattr(strategy, "dim"):
                raise AttributeError(
                    f"Resolver.{field.name} "
                    f"({type(strategy).__name__}) is missing required "
                    f"'dim' attribute"
                )
            if strategy.dim not in (required, Dim.BOTH):
                raise ValueError(
                    f"Resolver.{field.name} "
                    f"({type(strategy).__name__}) has dim={strategy.dim}, "
                    f"incompatible with is_3d={self.is_3d}; "
                    f"expected {required} or {Dim.BOTH}"
                )


__all__ = [
    "SimulationEngine",
]
