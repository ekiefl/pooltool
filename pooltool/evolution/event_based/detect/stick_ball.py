from __future__ import annotations

import numpy as np

import pooltool.constants as const
from pooltool.events import Event, EventType, stick_ball_collision
from pooltool.evolution.event_based._utils import _system_has_energy
from pooltool.evolution.event_based.cache import CollisionCache
from pooltool.system.datatypes import System


def get_next_stick_ball_event(shot: System, collision_cache: CollisionCache) -> Event:
    """Detect the next stick-ball collision.

    Stick-ball events fire only at t=0, when the system is at rest, the cue ball is
    in play, and a cue strike is queued (V0 > 0).
    """
    cache = collision_cache.times.setdefault(EventType.STICK_BALL, {})

    obj_ids = (shot.cue.id, shot.cue.cue_ball_id)

    if obj_ids in cache:
        return stick_ball_collision(
            stick=shot.cue,
            ball=shot.balls[shot.cue.cue_ball_id],
            time=cache[obj_ids],
        )

    cue_ball_in_play = shot.balls[shot.cue.cue_ball_id].state.s not in const.out_of_play
    if (
        shot.t == 0
        and cue_ball_in_play
        and not _system_has_energy(shot)
        and shot.cue.V0 > 0
    ):
        cache[obj_ids] = 0.0
    else:
        cache[obj_ids] = np.inf

    return stick_ball_collision(
        stick=shot.cue,
        ball=shot.balls[shot.cue.cue_ball_id],
        time=cache[obj_ids],
    )
