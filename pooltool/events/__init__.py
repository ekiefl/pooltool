#! /usr/bin/env python

from pooltool.events._events import Event, Events, EventType, event_resolvers


def null_event(time: float) -> Event:
    return Event(event_type=EventType.NONE, agents=[], time=time)
