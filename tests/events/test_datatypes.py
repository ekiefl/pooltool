from pathlib import Path
from typing import List

import pytest

from pooltool.events.datatypes import Event, EventType
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.table.components import (
    CircularCushionSegment,
    LinearCushionSegment,
    Pocket,
)
from pooltool.system.datatypes import System


@pytest.fixture
def example_events() -> List[Event]:
    """
    Returns the list of Event objects from simulating the example system.
    """
    return System.load(Path(__file__).parent / "example_system.msgpack").events


def test_get_ball_success(example_events: List[Event]):
    """
    Find an event that involves a ball (e.g. BALL_BALL or STICK_BALL)
    and verify we can retrieve the ball by ID.
    """
    # We'll look for a BALL_BALL event that (based on your snippet) should have agents: ('cue', '1')
    event = next(e for e in example_events if e.event_type == EventType.BALL_BALL)

    # Try retrieving the ball named "cue"
    cue_ball = event.get_ball("cue", initial=False)  # final state by default
    assert isinstance(cue_ball, Ball)
    assert cue_ball.id == "cue"

    # Also retrieve the "1" ball by initial state
    ball_1_initial = event.get_ball("1", initial=True)
    assert isinstance(ball_1_initial, Ball)
    assert ball_1_initial.id == "1"


def test_get_ball_no_ball_in_event(example_events: List[Event]):
    """
    Attempt to retrieve a ball from an event type that doesn't involve a ball, expecting ValueError.
    """
    null_event = example_events[0]
    assert null_event.event_type == EventType.NONE

    with pytest.raises(ValueError, match="does not involve a Ball"):
        null_event.get_ball("dummy")


def test_get_ball_wrong_id(example_events: List[Event]):
    """
    Attempt to retrieve a ball using an ID not present in a ball-involving event.
    """
    event = next(e for e in example_events if e.event_type == EventType.STICK_BALL)

    with pytest.raises(ValueError, match="No agent of type ball"):
        event.get_ball("1")


def test_get_cushion_success(example_events: List[Event]):
    """
    Find a BALL_LINEAR_CUSHION or BALL_CIRCULAR_CUSHION event and verify we can retrieve the cushion.
    """
    # Agents: ('cue','6')
    linear_event = next(
        e for e in example_events if e.event_type == EventType.BALL_LINEAR_CUSHION
    )

    cushion_obj = linear_event.get_cushion("6")
    assert isinstance(cushion_obj, LinearCushionSegment)
    assert cushion_obj.id == "6"

    # Agents ('cue', '8t')
    circular_event = next(
        e for e in example_events if e.event_type == EventType.BALL_CIRCULAR_CUSHION
    )
    cushion_obj_circ = circular_event.get_cushion("8t")
    assert isinstance(cushion_obj_circ, CircularCushionSegment)
    assert cushion_obj_circ.id == "8t"


def test_get_cushion_not_in_event(example_events: List[Event]):
    """
    Attempt to retrieve a cushion from an event that doesn't involve one.
    """
    event = next(e for e in example_events if e.event_type == EventType.BALL_BALL)
    with pytest.raises(ValueError, match="does not involve a cushion"):
        event.get_cushion("8t")


def test_get_pocket_success(example_events: List[Event]):
    """
    Find a BALL_POCKET event (agents: ('1','rt') in your snippet) and retrieve the pocket.
    """
    pocket_event = next(
        e for e in example_events if e.event_type == EventType.BALL_POCKET
    )
    pocket_obj = pocket_event.get_pocket("rt", initial=False)
    assert isinstance(pocket_obj, Pocket)
    assert pocket_obj.id == "rt"


def test_get_pocket_not_in_event(example_events: List[Event]):
    """
    Attempt to retrieve a pocket from a non-pocket event, expecting ValueError.
    """
    event = next(e for e in example_events if e.event_type == EventType.BALL_BALL)
    with pytest.raises(
        ValueError, match="Event of type ball_ball does not involve a Pocket"
    ):
        event.get_pocket("rt")


def test_get_pocket_missing_id(example_events: List[Event]):
    """
    Attempt to retrieve a pocket with an ID that doesn't match the event's pocket.
    """
    pocket_event = next(
        e for e in example_events if e.event_type == EventType.BALL_POCKET
    )
    with pytest.raises(
        ValueError, match="No agent of type pocket with ID 'non_existent_pocket_id'"
    ):
        pocket_event.get_pocket("non_existent_pocket_id")
