from __future__ import annotations

from itertools import combinations

import numpy as np

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.events import Event, EventType, ball_ball_collision, null_event
from pooltool.evolution.event_based.cache import CollisionCache
from pooltool.physics.motion.solve import ball_ball_collision_time
from pooltool.system.datatypes import System


def get_next_ball_ball_2d_event(shot: System, collision_cache: CollisionCache) -> Event:
    """Detect the next ball-ball collision in 2D mode."""
    cache = collision_cache.times.setdefault(EventType.BALL_BALL, {})

    for ball1, ball2 in combinations(shot.balls.values(), 2):
        ball_pair = (ball1.id, ball2.id)
        if ball_pair in cache:
            continue

        ball1_state = ball1.state
        ball1_params = ball1.params

        ball2_state = ball2.state
        ball2_params = ball2.params

        if ball1_state.s == const.pocketed or ball2_state.s == const.pocketed:
            cache[ball_pair] = np.inf
        elif (
            ball1_state.s in const.nontranslating
            and ball2_state.s in const.nontranslating
        ):
            cache[ball_pair] = np.inf
        elif ptmath.is_overlapping(
            ball1_state.rvw,
            ball2_state.rvw,
            ball1_params.R,
            ball2_params.R,
        ):
            cache[ball_pair] = shot.t
        else:
            dtau_E = ball_ball_collision_time(
                rvw1=ball1_state.rvw,
                rvw2=ball2_state.rvw,
                s1=ball1_state.s,
                s2=ball2_state.s,
                mu1=(
                    ball1_params.u_s
                    if ball1_state.s == const.sliding
                    else ball1_params.u_r
                ),
                mu2=(
                    ball2_params.u_s
                    if ball2_state.s == const.sliding
                    else ball2_params.u_r
                ),
                m1=ball1_params.m,
                m2=ball2_params.m,
                g1=ball1_params.g,
                g2=ball2_params.g,
                R=ball1_params.R,
            )
            cache[ball_pair] = shot.t + dtau_E

    if not cache:
        return null_event(np.inf)

    ball_pair = min(cache, key=lambda k: cache[k])

    return ball_ball_collision(
        ball1=shot.balls[ball_pair[0]],
        ball2=shot.balls[ball_pair[1]],
        time=cache[ball_pair],
    )


def get_next_ball_ball_3d_event(shot: System, collision_cache: CollisionCache) -> Event:
    return null_event(np.inf)
