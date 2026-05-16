"""The simulation engine of pooltool"""

from __future__ import annotations

import attrs

from pooltool.evolution.event_based.detect import EventDetector
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
        event_detector:
            The strategy responsible for detecting the next event.
    """

    resolver: Resolver = attrs.field(factory=Resolver.default)
    event_detector: EventDetector = attrs.field(factory=EventDetector.default)


__all__ = [
    "SimulationEngine",
]
