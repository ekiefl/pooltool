#! /usr/bin/env python

from __future__ import annotations

from typing import Dict, Set, Tuple

import attrs
import numpy as np

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.events import (
    AgentType,
    Event,
    EventType,
    null_event,
    rolling_spinning_transition,
    rolling_stationary_transition,
    sliding_rolling_transition,
    spinning_stationary_transition,
)
from pooltool.events.utils import event_type_to_ball_indices
from pooltool.objects.ball.datatypes import Ball
from pooltool.system.datatypes import System


def _null() -> Dict[str, Event]:
    return {"null": null_event(time=np.inf)}


@attrs.define
class TransitionCache:
    """A cache for managing and retrieving the next transition events for balls.

    This class maintains a dictionary of transitions, where each key is ball ID, and
    each value is the next transition associated with that object.

    Attributes:
        transitions:
            A dictionary mapping ball IDs to their corresponding next event.

    See Also:
        - For practical and historical reasons, events are cached differently depending
          on whether they are collision events or transition events. For collision
          event caching, see :class:`CollisionCache`.
    """

    transitions: Dict[str, Event] = attrs.field(factory=_null)

    def get_next(self) -> Event:
        return min(
            (trans for trans in self.transitions.values()), key=lambda event: event.time
        )

    def update(self, event: Event) -> None:
        """Update transition cache for all balls in Event"""
        for agent in event.agents:
            if agent.agent_type == AgentType.BALL:
                assert isinstance(ball := agent.final, Ball)
                self.transitions[agent.id] = _next_transition(ball)

    @classmethod
    def create(cls, shot: System) -> TransitionCache:
        return cls(
            {ball_id: _next_transition(ball) for ball_id, ball in shot.balls.items()}
        )


def _next_transition(ball: Ball) -> Event:
    if ball.state.s == const.stationary or ball.state.s == const.pocketed:
        return null_event(time=np.inf)

    elif ball.state.s == const.spinning:
        dtau_E = ptmath.get_spin_time(
            ball.state.rvw, ball.params.R, ball.params.u_sp, ball.params.g
        )
        return spinning_stationary_transition(ball, ball.state.t + dtau_E)

    elif ball.state.s == const.rolling:
        dtau_E_spin = ptmath.get_spin_time(
            ball.state.rvw, ball.params.R, ball.params.u_sp, ball.params.g
        )
        dtau_E_roll = ptmath.get_roll_time(
            ball.state.rvw, ball.params.u_r, ball.params.g
        )

        if dtau_E_spin > dtau_E_roll:
            return rolling_spinning_transition(ball, ball.state.t + dtau_E_roll)
        else:
            return rolling_stationary_transition(ball, ball.state.t + dtau_E_roll)

    elif ball.state.s == const.sliding:
        dtau_E = ptmath.get_slide_time(
            ball.state.rvw, ball.params.R, ball.params.u_s, ball.params.g
        )
        return sliding_rolling_transition(ball, ball.state.t + dtau_E)

    else:
        raise NotImplementedError(f"Unknown '{ball.state.s=}'")


class _IndexedDict(dict):
    def __init__(self, cache, event_type):
        super().__init__()
        self._cache = cache
        self._event_type = event_type

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._cache._add_to_index(self._event_type, key)

    def __delitem__(self, key):
        super().__delitem__(key)
        self._cache._remove_from_index(self._event_type, key)


class _IndexedTimesMap(dict):
    def __init__(self, cache):
        super().__init__()
        self._cache = cache

    def setdefault(self, key, default=None):
        if key not in self:
            super().__setitem__(key, _IndexedDict(self._cache, key))
        return super().__getitem__(key)


@attrs.define
class CollisionCache:
    """A cache for storing and managing collision times between objects.

    This class is used as a cache for possible future collision times. By caching
    collision times whenever they are calculated, re-calculating them during each step
    of the shot evolution algorithm can be avoided in many instances.

    It also provides functionality to invalidate cached events based on realized events,
    ensuring that outdated data does not persist in the cache. For example, if a
    ball-transition event for ball with ID "6" is passed to :meth:`invalidate`, all
    cached event times involving ball ID "6" are removed from the cache, since they are
    no longer valid.

    Attributes:
        times:
            A dictionary where each key is an event type, and each value is another
            dictionary mapping tuples of object IDs to their corresponding collision
            times.

    Properties:
        size:
            The total number of cached events.

    See Also:
        - For practical and historical reasons, events are cached differently depending
          on whether they are collision events or transition events. For transition
          event caching, see :class:`TransitionCache`.
    """

    times: Dict[EventType, Dict[Tuple[str, str], float]] = attrs.field(factory=dict)
    _keys_by_id: Dict[str, Set[Tuple[EventType, Tuple[str, str]]]] = attrs.field(factory=dict, init=False, repr=False)

    @property
    def size(self) -> int:
        return sum(len(cache) for cache in self.times.values())

    def _get_invalid_ball_ids(self, event: Event) -> Set[str]:
        return {
            event.ids[ball_idx]
            for ball_idx in event_type_to_ball_indices[event.event_type]
        }

    def __attrs_post_init__(self) -> None:
        self.times = _IndexedTimesMap(self)

    def invalidate(self, event: Event) -> None:
        invalid_ids = self._get_invalid_ball_ids(event)
        to_delete: Set[Tuple[EventType, Tuple[str, str]]] = set()
        for obj_id in invalid_ids:
            for etype, key in self._keys_by_id.get(obj_id, set()):
                to_delete.add((etype, key))
        for etype, key in to_delete:
            cache = self.times.get(etype)
            if cache is not None and key in cache:
                del cache[key]

    @classmethod
    def create(cls, shot: System | None = None) -> CollisionCache:
        """Create a collision cache, optionally precomputing all possible event keys for a shot."""
        cache = cls()
        if shot is not None:
            cache._init_possible_pairs(shot)
        return cache

    def _add_to_index(self, event_type: EventType, key: Tuple[str, str]) -> None:
        for idx in event_type_to_ball_indices.get(event_type, ()):
            obj_id = key[idx]
            self._keys_by_id.setdefault(obj_id, set()).add((event_type, key))

    def _remove_from_index(self, event_type: EventType, key: Tuple[str, str]) -> None:
        for idx in event_type_to_ball_indices.get(event_type, ()):
            obj_id = key[idx]
            entries = self._keys_by_id.get(obj_id)
            if entries:
                entries.discard((event_type, key))
                if not entries:
                    del self._keys_by_id[obj_id]

    def _init_possible_pairs(self, shot: System) -> None:
        """Precompute all possible collision key tuples for each supported event type."""
        # Ball-ball pairs
        from itertools import combinations

        ball_ids = list(shot.balls.keys())
        self._possible_pairs: dict[EventType, list[tuple[str, str]]] = {}
        self._possible_pairs[EventType.BALL_BALL] = list(combinations(ball_ids, 2))

        # Ball-circular cushion pairs
        circ = []
        for b in ball_ids:
            for cushion in shot.table.cushion_segments.circular.values():
                circ.append((b, cushion.id))
        self._possible_pairs[EventType.BALL_CIRCULAR_CUSHION] = circ

        # Ball-linear cushion pairs
        lin = []
        for b in ball_ids:
            for cushion in shot.table.cushion_segments.linear.values():
                lin.append((b, cushion.id))
        self._possible_pairs[EventType.BALL_LINEAR_CUSHION] = lin

        # Ball-pocket pairs
        pk = []
        for b in ball_ids:
            for pocket in shot.table.pockets.values():
                pk.append((b, pocket.id))
        self._possible_pairs[EventType.BALL_POCKET] = pk
