from __future__ import annotations

from typing import Protocol

import attrs

from pooltool.events import Event, EventType, ball_table_collision
from pooltool.evolution.event_based.cache import CollisionCache
from pooltool.physics.motion.solve import ball_table_collision_time
from pooltool.system.datatypes import System


class BallTableDetectionStrategy(Protocol):
    """Ball-table detection models must satisfy this protocol.

    Unlike the other detection-strategy protocols, this one does not declare a
    ``dim`` attribute.
    """

    def get_next(self, shot: System, collision_cache: CollisionCache) -> Event: ...


@attrs.define
class BallTableDetection:
    """Detects the next ball-table collision in the system."""

    def get_next(self, shot: System, collision_cache: CollisionCache) -> Event:
        cache = collision_cache.times.setdefault(EventType.BALL_TABLE, {})

        for ball in shot.balls.values():
            obj_ids = (ball.id,)
            if obj_ids in cache:
                continue
            dtau_E = ball_table_collision_time(
                rvw=ball.state.rvw,
                s=ball.state.s,
                g=ball.params.g,
                R=ball.params.R,
            )
            cache[obj_ids] = shot.t + dtau_E

        obj_ids = min(cache, key=lambda k: cache[k])

        return ball_table_collision(
            ball=shot.balls[obj_ids[0]],
            time=cache[obj_ids],
        )
