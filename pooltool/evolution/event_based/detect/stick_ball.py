from __future__ import annotations

from typing import Protocol

import attrs
import numpy as np

from pooltool.events import Event, EventType, stick_ball_collision
from pooltool.evolution.event_based._utils import _system_has_energy
from pooltool.evolution.event_based.cache import CollisionCache
from pooltool.system.datatypes import System


class StickBallDetectionStrategy(Protocol):
    """Stick-ball detection models must satisfy this protocol."""

    def get_next(self, shot: System, collision_cache: CollisionCache) -> Event: ...


@attrs.define
class StickBallDetection:
    """Stick-ball collision detection.

    Stick-ball events fire only at t=0, when the system is at rest and a cue strike is
    queued (V0 > 0).
    """

    def get_next(self, shot: System, collision_cache: CollisionCache) -> Event:
        cache = collision_cache.times.setdefault(EventType.STICK_BALL, {})

        obj_ids = (shot.cue.id, shot.cue.cue_ball_id)

        if obj_ids in cache:
            return stick_ball_collision(
                stick=shot.cue,
                ball=shot.balls[shot.cue.cue_ball_id],
                time=cache[obj_ids],
            )

        if shot.t == 0 and not _system_has_energy(shot) and shot.cue.V0 > 0:
            cache[obj_ids] = 0.0
        else:
            cache[obj_ids] = np.inf

        return stick_ball_collision(
            stick=shot.cue,
            ball=shot.balls[shot.cue.cue_ball_id],
            time=cache[obj_ids],
        )
