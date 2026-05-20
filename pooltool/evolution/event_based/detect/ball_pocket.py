from __future__ import annotations

import numpy as np

import pooltool.constants as const
from pooltool.events import Event, EventType, ball_pocket_collision, null_event
from pooltool.evolution.event_based.cache import CollisionCache
from pooltool.physics.motion.solve import (
    ball_pocket_collision_time,
    ball_pocket_collision_time_airborne,
)
from pooltool.system.datatypes import System


def get_next_ball_pocket_2d_event(
    shot: System, collision_cache: CollisionCache
) -> Event:
    """Detect the next ball-pocket collision in 2D mode."""
    if not shot.table.has_pockets:
        return null_event(np.inf)

    cache = collision_cache.times.setdefault(EventType.BALL_POCKET, {})

    for ball in shot.balls.values():
        state = ball.state
        params = ball.params

        for pocket in shot.table.pockets.values():
            obj_ids = (ball.id, pocket.id)

            if obj_ids in cache:
                continue

            if ball.state.s in const.nontranslating:
                cache[obj_ids] = np.inf
                continue

            dtau_E = ball_pocket_collision_time(
                rvw=state.rvw,
                s=state.s,
                a=pocket.a,
                b=pocket.b,
                r=pocket.radius,
                mu=(params.u_s if state.s == const.sliding else params.u_r),
                m=params.m,
                g=params.g,
                R=params.R,
            )
            cache[obj_ids] = shot.t + dtau_E

    ball_id, pocket_id = min(cache, key=lambda k: cache[k])

    return ball_pocket_collision(
        ball=shot.balls[ball_id],
        pocket=shot.table.pockets[pocket_id],
        time=cache[(ball_id, pocket_id)],
    )


def get_next_ball_pocket_3d_event(
    shot: System, collision_cache: CollisionCache
) -> Event:
    """Detect the next ball-pocket collision in 3D mode.

    Airborne balls use :func:`ball_pocket_collision_time_airborne`, which models the
    pocket as a vertical cylinder and accounts for the parabolic z-trajectory.
    Non-airborne, translating balls delegate to the same 2D detection routine as
    :func:`get_next_ball_pocket_2d_event`.
    """
    if not shot.table.has_pockets:
        return null_event(np.inf)

    cache = collision_cache.times.setdefault(EventType.BALL_POCKET, {})

    for ball in shot.balls.values():
        state = ball.state
        params = ball.params

        for pocket in shot.table.pockets.values():
            obj_ids = (ball.id, pocket.id)

            if obj_ids in cache:
                continue

            if state.s in const.nontranslating:
                cache[obj_ids] = np.inf
                continue

            if state.s == const.airborne:
                dtau_E = ball_pocket_collision_time_airborne(
                    rvw=state.rvw,
                    a=pocket.a,
                    b=pocket.b,
                    r=pocket.radius,
                    g=params.g,
                    R=params.R,
                )
            else:
                dtau_E = ball_pocket_collision_time(
                    rvw=state.rvw,
                    s=state.s,
                    a=pocket.a,
                    b=pocket.b,
                    r=pocket.radius,
                    mu=(params.u_s if state.s == const.sliding else params.u_r),
                    m=params.m,
                    g=params.g,
                    R=params.R,
                )
            cache[obj_ids] = shot.t + dtau_E

    ball_id, pocket_id = min(cache, key=lambda k: cache[k])

    return ball_pocket_collision(
        ball=shot.balls[ball_id],
        pocket=shot.table.pockets[pocket_id],
        time=cache[(ball_id, pocket_id)],
    )
