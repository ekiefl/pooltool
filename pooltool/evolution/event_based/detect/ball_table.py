from __future__ import annotations

from pooltool.events import Event, EventType, ball_table_collision
from pooltool.evolution.event_based.cache import CollisionCache
from pooltool.physics.motion.solve import ball_table_collision_time
from pooltool.system.datatypes import System


def get_next_ball_table_event(shot: System, collision_cache: CollisionCache) -> Event:
    """Detect the next ball-table collision (airborne ball landing).

    Only invoked when ``EventDetector.is_3d`` is True — ball-table events are
    a 3D-only concept.
    """
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
