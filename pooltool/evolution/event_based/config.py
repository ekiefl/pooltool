from pooltool.events.datatypes import EventType

INCLUDED_EVENTS = {
    EventType.NONE,
    EventType.BALL_BALL,
    EventType.BALL_LINEAR_CUSHION,
    EventType.BALL_CIRCULAR_CUSHION,
    EventType.BALL_POCKET,
    EventType.STICK_BALL,
    EventType.SPINNING_STATIONARY,
    EventType.ROLLING_STATIONARY,
    EventType.ROLLING_SPINNING,
    EventType.SLIDING_ROLLING,
}

DORMANT_IN_2D: frozenset[str] = frozenset({"ball_table"})
"""Resolver/EventDetector field names that are dormant in 2D mode because the detection
layer doesn't emit their associated event types. In 2D, the ``dim`` of these fields is
not validated against ``SimulationEngine.is_3d`` - any tag is safe because the strategy
will never be invoked. In 3D, they are validated normally so a misdeclared ball-table
strategy is still caught."""
