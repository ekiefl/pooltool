from typing import List, Union

from pooltool.events.datatypes import Event, EventType
from pooltool.objects.ball.datatypes import Ball


def filter_type(
    events: List[Event], types: Union[EventType, List[EventType]]
) -> List[Event]:
    """Return events in chronological order that are of an event type or types

    Parameters
    ==========
    types : str or list of str
        Event types to be filtered by. E.g.
        pooltool.events.EventType.BALL_CIRCULAR_CUSHION or equivalently,
        'ball_circular_cushion'

    Returns
    =======
    events:
        A subset of events that are of the specified types.
    """

    if isinstance(types, str):
        types = [types]

    new: List[Event] = []
    for event in events:
        if event.event_type in types:
            new.append(event)

    return new


def filter_ball(
    events: List[Event], balls: Union[str, List[str]], keep_nonevent: bool = False
) -> List[Event]:
    """Return events in chronological order that involve a collection of balls

    Returns
    =======
    events:
        A subset of events involving specified balls.
    """

    if isinstance(balls, str):
        balls = [balls]

    new: List[Event] = []
    for event in events:
        if keep_nonevent and event.event_type == EventType.NONE:
            new.append(event)
        else:
            for agent in event.agents:
                if isinstance(agent.initial, Ball) and agent.initial.id in balls:
                    new.append(event)
                    break

    return new


def filter_time(events: List[Event], t: float) -> List[Event]:
    """Return events in chronological order after a certain time

    Parameters
    ==========
    t : float
        time after which you want events for

    Returns
    =======
    events:
        A subset of events occurring after specified time, non-inclusive.
    """

    new: List[Event] = []
    for event in reversed(events):
        if event.time > t:
            new.append(event)
        else:
            break

    return new[::-1]
