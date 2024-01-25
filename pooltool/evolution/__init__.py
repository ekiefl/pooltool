from pooltool.evolution.continuize import continuize
from pooltool.evolution.event_based.simulate import simulate as simulate_event_based

simulate = simulate_event_based

__all__ = [
    "continuize",
    "simulate_event_based",
    "simulate",
]
