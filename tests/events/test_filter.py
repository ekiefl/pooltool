import pytest
from numpy import inf

from pooltool.events import (
    ball_ball_collision,
    ball_linear_cushion_collision,
    null_event,
    rolling_stationary_transition,
    sliding_rolling_transition,
    stick_ball_collision,
)
from pooltool.events.datatypes import EventType
from pooltool.events.filter import (
    by_ball,
    by_time,
    by_type,
    filter_ball,
    filter_events,
    filter_time,
    filter_type,
)
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.cue.datatypes import Cue
from pooltool.objects.table.components import LinearCushionSegment


@pytest.fixture
def ball1():
    return Ball.dummy("1")


@pytest.fixture
def ball2():
    return Ball.dummy("2")


@pytest.fixture
def ball3():
    return Ball.dummy("3")


@pytest.fixture
def cue():
    # Cue ID is "1"
    return Cue("1")


@pytest.fixture
def cushion():
    return LinearCushionSegment.dummy()


@pytest.fixture
def events(ball1, ball2, ball3, cue, cushion):
    return [
        null_event(0),
        stick_ball_collision(cue, ball2, 1),
        sliding_rolling_transition(ball1, 2),
        ball_ball_collision(ball1, ball2, 3),
        sliding_rolling_transition(ball1, 4),
        sliding_rolling_transition(ball2, 5),
        rolling_stationary_transition(ball2, 6),
        ball_ball_collision(ball1, ball3, 7),
        sliding_rolling_transition(ball1, 8),
        sliding_rolling_transition(ball3, 9),
        rolling_stationary_transition(ball1, 10),
        ball_linear_cushion_collision(ball3, cushion, 12),
        null_event(inf),
    ]


def test_by_ball_single(events, ball1, ball2, ball3, cue):
    # Only events with
    result = filter_ball(events, "1")

    assert result == [
        sliding_rolling_transition(ball1, 2),
        ball_ball_collision(ball1, ball2, 3),
        sliding_rolling_transition(ball1, 4),
        ball_ball_collision(ball1, ball3, 7),
        sliding_rolling_transition(ball1, 8),
        rolling_stationary_transition(ball1, 10),
    ]

    # Null events included
    result_with_nonevents = filter_ball(events, "1", keep_nonevent=True)

    assert result_with_nonevents == [
        null_event(0),
        sliding_rolling_transition(ball1, 2),
        ball_ball_collision(ball1, ball2, 3),
        sliding_rolling_transition(ball1, 4),
        ball_ball_collision(ball1, ball3, 7),
        sliding_rolling_transition(ball1, 8),
        rolling_stationary_transition(ball1, 10),
        null_event(inf),
    ]

    # Cue stick is not in events, even though it has ID "1"
    assert stick_ball_collision(cue, ball2, 1) not in result

    # Null cases
    assert filter_ball(events, "") == []
    assert filter_ball(events, "fake") == []
    assert filter_ball(events, "fake", keep_nonevent=True) == [
        null_event(0),
        null_event(inf),
    ]


def test_by_ball_multi(events, ball1, ball2, ball3, cue):
    # Single element list works fine
    assert filter_ball(events, ["1"]) == [
        sliding_rolling_transition(ball1, 2),
        ball_ball_collision(ball1, ball2, 3),
        sliding_rolling_transition(ball1, 4),
        ball_ball_collision(ball1, ball3, 7),
        sliding_rolling_transition(ball1, 8),
        rolling_stationary_transition(ball1, 10),
    ]

    # Multi element cases (with nonevents)
    assert filter_ball(events, ["1", "2"], keep_nonevent=True) == [
        null_event(0),
        stick_ball_collision(cue, ball2, 1),
        sliding_rolling_transition(ball1, 2),
        ball_ball_collision(ball1, ball2, 3),
        sliding_rolling_transition(ball1, 4),
        sliding_rolling_transition(ball2, 5),
        rolling_stationary_transition(ball2, 6),
        ball_ball_collision(ball1, ball3, 7),
        sliding_rolling_transition(ball1, 8),
        rolling_stationary_transition(ball1, 10),
        null_event(inf),
    ]

    # Null cases
    assert filter_ball(events, []) == []
    assert filter_ball(events, ["fake", "fake2"]) == []
    assert filter_ball(events, ["fake", "fake2"], keep_nonevent=True) == [
        null_event(0),
        null_event(inf),
    ]


def test_by_type_single(events, ball1, ball2, ball3, cue):
    assert filter_type(events, EventType.STICK_BALL) == [
        stick_ball_collision(cue, ball2, 1),
    ]

    assert filter_type(events, EventType.SLIDING_ROLLING) == [
        sliding_rolling_transition(ball1, 2),
        sliding_rolling_transition(ball1, 4),
        sliding_rolling_transition(ball2, 5),
        sliding_rolling_transition(ball1, 8),
        sliding_rolling_transition(ball3, 9),
    ]


def test_by_type_multi(events, ball1, ball2, ball3, cue):
    assert filter_type(events, [EventType.STICK_BALL, EventType.SLIDING_ROLLING]) == [
        stick_ball_collision(cue, ball2, 1),
        sliding_rolling_transition(ball1, 2),
        sliding_rolling_transition(ball1, 4),
        sliding_rolling_transition(ball2, 5),
        sliding_rolling_transition(ball1, 8),
        sliding_rolling_transition(ball3, 9),
    ]


def test_by_time(events, cue, ball1, ball2, ball3, cushion):
    # After t (non-inclusive)
    assert filter_time(events, 4) == [
        sliding_rolling_transition(ball2, 5),
        rolling_stationary_transition(ball2, 6),
        ball_ball_collision(ball1, ball3, 7),
        sliding_rolling_transition(ball1, 8),
        sliding_rolling_transition(ball3, 9),
        rolling_stationary_transition(ball1, 10),
        ball_linear_cushion_collision(ball3, cushion, 12),
        null_event(inf),
    ]

    # Before t (non-inclusive)
    assert filter_time(events, 4, after=False) == [
        null_event(0),
        stick_ball_collision(cue, ball2, 1),
        sliding_rolling_transition(ball1, 2),
        ball_ball_collision(ball1, ball2, 3),
    ]

    # Fails if not sorted
    with pytest.raises(ValueError, match="chronological"):
        filter_time(events[::-1], 4)


def test_chaining(events, ball1, ball2, ball3, cushion):
    filter_result = filter_events(
        events,
        by_ball(["2", "3"]),
        by_time(t=3),
        by_type(
            [
                EventType.BALL_LINEAR_CUSHION,
                EventType.SLIDING_ROLLING,
                EventType.BALL_BALL,
            ]
        ),
    )

    assert filter_result == [
        sliding_rolling_transition(ball2, 5),
        ball_ball_collision(ball1, ball3, 7),
        sliding_rolling_transition(ball3, 9),
        ball_linear_cushion_collision(ball3, cushion, 12),
    ]
