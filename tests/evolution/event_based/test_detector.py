import pytest

from pooltool.events import (
    Event,
    ball_ball_collision,
    ball_circular_cushion_collision,
    ball_linear_cushion_collision,
    ball_pocket_collision,
    null_event,
    sliding_rolling_transition,
    stick_ball_collision,
)
from pooltool.evolution.event_based.detect.detector import _get_event_priority
from pooltool.objects import Ball, Cue, Table
from pooltool.system import System


@pytest.fixture
def system() -> System:
    return System(
        cue=Cue(cue_ball_id="cue"),
        table=Table.default(),
        balls=(
            Ball.create("cue", xy=(0.5, 0.5)),
            Ball.create("1", xy=(0.7, 0.5)),
            Ball.create("2", xy=(0.9, 0.5)),
        ),
    )


def _make_events(s: System) -> dict[str, Event]:
    """One event of each type, all at the same simulation time."""
    return {
        "stick_ball": stick_ball_collision(stick=s.cue, ball=s.balls["cue"], time=0),
        "pocket": ball_pocket_collision(
            ball=s.balls["cue"],
            pocket=next(iter(s.table.pockets.values())),
            time=0,
        ),
        "transition": sliding_rolling_transition(s.balls["cue"], time=0),
        "ball_ball": ball_ball_collision(s.balls["cue"], s.balls["1"], time=0),
        "linear_cushion": ball_linear_cushion_collision(
            ball=s.balls["cue"],
            cushion=next(iter(s.table.cushion_segments.linear.values())),
            time=0,
        ),
        "circular_cushion": ball_circular_cushion_collision(
            ball=s.balls["cue"],
            cushion=next(iter(s.table.cushion_segments.circular.values())),
            time=0,
        ),
        "none": null_event(time=0),
    }


def test_event_priority_sorts_by_tier(system):
    """All event types at the same time sort in priority order."""
    events = _make_events(system)

    def sort_key(event: Event) -> tuple[int, float]:
        tier, energy = _get_event_priority(event, system)
        return (tier, -energy)

    sorted_events = sorted(events.values(), key=sort_key)
    tiers = [_get_event_priority(e, system)[0] for e in sorted_events]

    assert tiers == sorted(tiers), "tiers should be non-decreasing"
    assert sorted_events[0] is events["stick_ball"]
    assert sorted_events[-1] is events["none"]
