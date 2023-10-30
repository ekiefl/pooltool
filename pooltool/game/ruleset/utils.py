from typing import List, Optional

from pooltool.events.datatypes import EventType
from pooltool.events.filter import by_ball, by_type, filter_events, filter_type
from pooltool.system.datatypes import System


def get_pocketed_ball_ids(shot: System) -> List[str]:
    pocket_events = filter_type(shot.events, EventType.BALL_POCKET)
    return [event.agents[0].id for event in pocket_events]


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
