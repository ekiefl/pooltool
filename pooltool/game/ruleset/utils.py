from typing import List, Optional, Set

import pooltool.constants as const
from pooltool.events.datatypes import EventType
from pooltool.events.filter import by_ball, by_type, filter_events, filter_type
from pooltool.objects.ball.datatypes import Ball
from pooltool.system.datatypes import System


def get_pocketed_ball_ids_during_shot(
    shot: System, exclude: Optional[Set[str]] = None
) -> List[str]:
    """Get list of ball IDs pocketed during the shot

    See also get_pocketed_ball_ids
    """
    if exclude is None:
        exclude = set()

    return [
        event.agents[0].id
        for event in filter_type(shot.events, EventType.BALL_POCKET)
        if event.agents[0].id not in exclude
    ]


def get_pocketed_ball_ids(shot: System) -> List[str]:
    """Get list of ball IDs that are in the pocketed state (by end of shot)

    See also get_pocketed_ball_ids_during_shot
    """
    return [ball.id for ball in shot.balls.values() if ball.state.s == const.pocketed]


def get_id_of_first_ball_hit(shot: System, cue: str = "cue") -> Optional[str]:
    cue_collisions = filter_events(
        shot.events,
        by_ball(cue),
        by_type(EventType.BALL_BALL),
    )

    if not len(cue_collisions):
        return None

    id1, id2 = cue_collisions[0].ids
    return id1 if id1 != cue else id2


def is_ball_pocketed(shot: System, ball_id: str) -> bool:
    return any(
        ball_id in event.agents[0].id
        for event in filter_type(shot.events, EventType.BALL_POCKET)
    )


def respot(
    shot: System, ball_id: str, x: float, y: float, z: Optional[float] = None
) -> None:
    """Respot a ball

    Args:
        z:
            If not provided, z is set to the ball's radius

    Notes
    =====
    - FIXME check if respot position overlaps with ball
    """
    R = shot.balls[ball_id].params.R

    if z is None:
        z = R

    if z > R:
        raise NotImplementedError("No airborne state exists")
        #  state = "airborne"
    else:
        state = const.stationary

    shot.balls[ball_id].state.rvw[0] = [x, y, z]
    shot.balls[ball_id].state.s = state


def get_lowest_ball(shot: System, at_start: bool) -> Ball:
    """Get the lowest ball on the table at start or end of shot

    Args:
        at_start:
            If True, the lowest ball on the table at t=0 is calculated. If False,
            the lowest ball at the end of the shot (t=inf) is calculated. The latter
            returns a different result if the lowest ball on the table was pocketed
    """
    _dummy = "10000"
    lowest = Ball.dummy(id=_dummy)

    history_idx = 0 if at_start else -1
    for ball in shot.balls.values():
        if ball.id == "cue":
            continue
        if ball.history[history_idx].s == const.pocketed:
            continue
        if int(ball.id) < int(lowest.id):
            lowest = ball

    assert lowest.id != _dummy, "No numbered balls on table"

    return lowest


def get_highest_ball(shot: System, at_start: bool) -> Ball:
    """Get the highest ball on the table at start or end of shot

    Args:
        at_start:
            If True, the highest ball on the table at t=0 is calculated. If False,
            the highest ball at the end of the shot (t=inf) is calculated. The latter
            returns a different result if the highest ball on the table was pocketed
    """
    _dummy = "0"
    highest = Ball.dummy(id=_dummy)

    history_idx = 0 if at_start else -1
    for ball in shot.balls.values():
        if ball.id == "cue":
            continue
        if ball.history[history_idx].s == const.pocketed:
            continue
        if int(ball.id) > int(highest.id):
            highest = ball

    assert highest.id != _dummy, "No numbered balls on table"

    return highest


def is_lowest_hit_first(shot: System) -> bool:
    if (ball_id := get_id_of_first_ball_hit(shot, cue="cue")) is None:
        return False

    return get_lowest_ball(shot, at_start=True).id == ball_id


def balls_that_hit_cushion(
    shot: System, exclude: Optional[Set[str]] = None
) -> Set[str]:
    if exclude is None:
        exclude = set()

    numbered_ball_ids = [
        ball.id for ball in shot.balls.values() if ball.id not in exclude
    ]

    cushion_events = filter_events(
        shot.events,
        by_type([EventType.BALL_LINEAR_CUSHION, EventType.BALL_CIRCULAR_CUSHION]),
        by_ball(numbered_ball_ids),
    )

    return set(event.agents[0].id for event in cushion_events)
