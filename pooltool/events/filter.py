from typing import Callable, List, Union

from pooltool.events.datatypes import AgentType, Event, EventType
from pooltool.objects.ball.datatypes import Ball

FilterFunc = Callable[[List[Event]], List[Event]]


def by_type(types: Union[EventType, List[EventType]]) -> FilterFunc:
    def func(events: List[Event]) -> List[Event]:
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
        _types: Union[EventType, List[EventType]]

        if isinstance(types, str):
            _types = [types]
        else:
            _types = types

        new: List[Event] = []
        for event in events:
            if event.event_type in _types:
                new.append(event)

        return new

    return func


def by_ball(ball_ids: Union[str, List[str]], keep_nonevent: bool = False) -> FilterFunc:
    def func(events: List[Event]) -> List[Event]:
        """Return events in chronological order that involve a collection of balls

        Returns
        =======
        events:
            A subset of events involving specified balls.
        """

        _ball_ids: Union[str, List[str]]
        if isinstance(ball_ids, str):
            _ball_ids = [ball_ids]
        else:
            _ball_ids = ball_ids

        new: List[Event] = []
        for event in events:
            if keep_nonevent and event.event_type == EventType.NONE:
                new.append(event)
            else:
                for agent in event.agents:
                    if agent.id in _ball_ids and agent.agent_type == AgentType.BALL:
                        new.append(event)
                        break

        return new

    return func


def by_time(t: float) -> FilterFunc:
    def func(events: List[Event]) -> List[Event]:
        """Return events in chronological order after a certain time

        Parameters
        ==========
        t : float
            time after which you want events for (non-inclusive)

        Returns
        =======
        events:
            A subset of events occurring after specified time, non-inclusive.
        """

        if not events == sorted(events, key=lambda event: event.time):
            raise ValueError("Event lists must be chronological")

        new: List[Event] = []
        for event in reversed(events):
            if event.time > t:
                new.append(event)
            else:
                break

        return new[::-1]

    return func


def chain(*funcs: FilterFunc) -> FilterFunc:
    def func(events: List[Event]) -> List[Event]:
        result = events
        for f in funcs:
            result = f(result)
        return result

    return func


def filter_events(events: List[Event], *funcs: FilterFunc) -> List[Event]:
    return chain(*funcs)(events)


def filter_type(
    events: List[Event], types: Union[EventType, List[EventType]]
) -> List[Event]:
    return by_type(types)(events)


def filter_ball(
    events: List[Event], ball_ids: Union[str, List[str]], keep_nonevent: bool = False
) -> List[Event]:
    return by_ball(ball_ids, keep_nonevent)(events)


def filter_time(events: List[Event], t: float) -> List[Event]:
    return by_time(t)(events)
