from typing import List, Optional

import pooltool.constants as const
from pooltool.events.datatypes import EventType
from pooltool.events.filter import by_ball, by_type, filter_events, filter_type
from pooltool.system.datatypes import System


def get_pocketed_ball_ids_during_shot(shot: System) -> List[str]:
    """Get list of ball IDs pocketed during the shot

    See also get_pocketed_ball_ids
    """
    pocket_events = filter_type(shot.events, EventType.BALL_POCKET)
    return [event.agents[0].id for event in pocket_events]


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
