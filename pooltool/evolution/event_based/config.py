from pooltool.events.datatypes import EventType

SOLVER = "numeric"

EPS_TIME = 1e-9
EPS_SPACE = 1e-9

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
