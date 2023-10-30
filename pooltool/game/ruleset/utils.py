from typing import List

from pooltool.events.datatypes import EventType
from pooltool.events.filter import filter_type
from pooltool.system.datatypes import System


def get_pocketed_ball_ids(shot: System) -> List[str]:
    pocket_events = filter_type(shot.events, EventType.BALL_POCKET)
    return [event.agents[0].id for event in pocket_events]
