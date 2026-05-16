"""The simulation engine of pooltool"""

from __future__ import annotations

import attrs

from pooltool.physics.resolve import Resolver


@attrs.define
class SimulationEngine:
    """A pluggable bundle of strategies used by the simulator.

    Holds the strategies that define how a simulation is carried out: how events are
    resolved and (in future) how they are detected. The simulator is handed an instance
    of this class and routes work to its components.

    Attributes:
        resolver:
            The strategy responsible for resolving events.
    """

    resolver: Resolver = attrs.field(factory=Resolver.default)


__all__ = [
    "SimulationEngine",
]
