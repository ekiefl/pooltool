from pooltool.events.datatypes import EventType

event_type_to_ball_indices: dict[EventType, set[int]] = {
    EventType.BALL_BALL: {0, 1},
    EventType.BALL_LINEAR_CUSHION: {0},
    EventType.BALL_CIRCULAR_CUSHION: {0},
    EventType.BALL_POCKET: {0},
    EventType.STICK_BALL: {1},
    EventType.BALL_TABLE: {0},
    EventType.SPINNING_STATIONARY: {0},
    EventType.ROLLING_STATIONARY: {0},
    EventType.ROLLING_SPINNING: {0},
    EventType.SLIDING_ROLLING: {0},
}
