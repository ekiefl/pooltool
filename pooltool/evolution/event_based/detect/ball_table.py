from __future__ import annotations

import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const
from pooltool.events import Event, EventType, ball_table_collision
from pooltool.evolution.event_based.cache import CollisionCache
from pooltool.physics.utils import get_airborne_time
from pooltool.system.datatypes import System


@jit(nopython=True, cache=const.use_numba_cache)
def ball_table_collision_time(
    rvw: NDArray[np.float64],
    s: int,
    g: float,
    R: float,
) -> float:
    """Time until an airborne ball's bottom touches the table plane.

    Returns ``np.inf`` if the ball is not airborne (no ball-table collision can
    occur for any other motion state).
    """
    if s != const.airborne:
        return np.inf
    return get_airborne_time(rvw=rvw, R=R, g=g)


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
