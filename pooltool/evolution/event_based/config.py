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
