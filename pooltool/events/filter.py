from typing import Callable, List, Union

from pooltool.events.datatypes import AgentType, Event, EventType

FilterFunc = Callable[[List[Event]], List[Event]]


def by_type(types: Union[EventType, List[EventType]]) -> FilterFunc:
    """Returns a function that filters events based on event type.

    Args:
        types:
            Event type(s) you want to include in your result. All others will be
            filtered.

    Returns:
        FilterFunc:
            A function that when passed a list of events, returns a filtered list
            containing only events matching the passed event type(s).
    """

    def func(events: List[Event]) -> List[Event]:
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
    """Returns a function that filters events based on ball IDs.

    Args:
        ball_ids:
            A collection of ball IDs.
        keep_nonevent:
            Retain non-events (:attr:`EventType.NONE`).

    Returns:
        FilterFunc:
            A function that when passed a list of events, returns a filtered list
            containing only events that involve balls matching the passed ball ID(s).
    """

    def func(events: List[Event]) -> List[Event]:
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


def by_time(t: float, after: bool = True) -> FilterFunc:
    """Returns a function that filter events with respect to a time cutoff.

    Args:
        t:
            The cutoff time for filtering events.
        after:
            If ``True``, return events after time ``t`` (non-inclusive).
            If ``False``, return events before time ``t`` (non-inclusive).

    Returns:
        FilterFunc:
            A function that when passed a list of events, returns a filtered list
            containing only events before or after the cutoff time, non-inclusive.
    """

    def func(events: List[Event]) -> List[Event]:
        if not events == sorted(events, key=lambda event: event.time):
            raise ValueError("Event lists must be chronological")

        new: List[Event] = []
        for event in events:
            if after and event.time > t:
                new.append(event)
            elif not after and event.time < t:
                new.append(event)

        return new

    return func


def _chain(*funcs: FilterFunc) -> FilterFunc:
    def func(events: List[Event]) -> List[Event]:
        result = events
        for f in funcs:
            result = f(result)
        return result

    return func


def filter_events(events: List[Event], *funcs: FilterFunc) -> List[Event]:
    """Filter events using multiple criteria.

    A convenient way to filter based multiple filtering criteria.

    Args:
        events:
            A list of chronological events.
        *funcs:
            An arbitrary number of functions that take a list of events as input, and
            gives a subset of that list as input. It sounds laborious--it's not. See
            *Examples*.

    Returns:
        List[Event]:
            A filtered event list containing only events passing the supplied criteria.

    Examples:

        Generate a list of events.

        >>> import pooltool as pt
        >>> system = pt.System.example()
        >>> system.cue.set_state(a=0.68)
        >>> pt.simulate(system, inplace=True)
        >>> events = system.events

        In this shot, both the cue-ball and the 1-ball are potted. We are interested in
        filtering for the cue-ball pocket event. Option 1 is to call :func:`filter_type`
        and then :func:`filter_ball`:

        >>> filtered_events = pt.events.filter_type(events, pt.EventType.BALL_POCKET)
        >>> filtered_events = pt.events.filter_ball(filtered_events, "cue")
        >>> event_of_interest = filtered_events[0]
        >>> event_of_interest
        <Event object at 0x7fa855e7e6c0>
         ├── type   : ball_pocket
         ├── time   : 3.231130101576186
         └── agents : ('cue', 'rt')

        Option 2, the better option, is to use :func:`filter_events`:

        >>> filtered_events = pt.events.filter_events(
        >>>     events,
        >>>     pt.events.by_type(pt.EventType.BALL_POCKET),
        >>>     pt.events.by_ball("cue"),
        >>> )
        >>> event_of_interest = filtered_events[0]
        >>> event_of_interest
        <Event object at 0x7fa855e7e6c0>
         ├── type   : ball_pocket
         ├── time   : 3.231130101576186
         └── agents : ('cue', 'rt')

    See Also:
        - If you're filtering based on a single criterion, you can consider using
          :func:`filter_type`, :func:`filter_ball`, :func:`filter_time`, etc.
    """
    return _chain(*funcs)(events)


def filter_type(
    events: List[Event], types: Union[EventType, List[EventType]]
) -> List[Event]:
    """Filter events based on event type.

    Args:
        events:
            A list of chronological events.
        types:
            Event type(s) you want to include in your result. All others will be
            filtered.

    Returns:
        List[Event]:
            A filtered event list containing only events matching the passed event
            type(s).

    See Also:
        - If you're filtering based on multiple criteria, you can (and should!) use
          :func:`filter_events`.
    """
    return by_type(types)(events)


def filter_ball(
    events: List[Event], ball_ids: Union[str, List[str]], keep_nonevent: bool = False
) -> List[Event]:
    """Filter events based on ball IDs.

    Args:
        events:
            A list of chronological events.
        ball_ids:
            A collection of ball IDs.
        keep_nonevent:
            Retain non-events (:attr:`EventType.NONE`).

    Returns:
        List[Event]:
            A filtered event list containing only events that involve balls matching the
            passed ball ID(s).

    See Also:
        - If you're filtering based on multiple criteria, you can (and should!) use
          :func:`filter_events`.
    """
    return by_ball(ball_ids, keep_nonevent)(events)


def filter_time(events: List[Event], t: float, after: bool = True) -> List[Event]:
    """Filter events with respect to a time cutoff.

    Args:
        events:
            A list of chronological events.
        t:
            The cutoff time for filtering events.
        after:
            If ``True``, return events after time ``t`` (non-inclusive).
            If ``False``, return events before time ``t`` (non-inclusive).

    Returns:
        List[Event]:
            A filtered event list containing only events before or after the cutoff
            time, non-inclusive.

    See Also:
        - If you're filtering based on multiple criteria, you can (and should!) use
          :func:`filter_events`.
    """
    return by_time(t, after)(events)
