from __future__ import annotations

from typing import Protocol

import attrs
import numpy as np

import pooltool.constants as const
from pooltool.events import (
    Event,
    EventType,
    ball_circular_cushion_collision,
    ball_linear_cushion_collision,
    null_event,
)
from pooltool.evolution.event_based.cache import CollisionCache
from pooltool.physics.dimensionality import Dim
from pooltool.physics.motion.solve import (
    ball_circular_cushion_collision_time,
    ball_linear_cushion_collision_time,
)
from pooltool.system.datatypes import System


class BallLCushionDetectionStrategy(Protocol):
    """Ball-vs-linear-cushion-segment detection models must satisfy this protocol."""

    dim: Dim

    def get_next(self, shot: System, collision_cache: CollisionCache) -> Event: ...


@attrs.define
class BallLCushionDetection:
    """Detects the next ball-vs-linear-cushion-segment collision in the system."""

    dim: Dim = attrs.field(default=Dim.TWO, init=False, repr=False)

    def get_next(self, shot: System, collision_cache: CollisionCache) -> Event:
        if not shot.table.has_linear_cushions:
            return null_event(np.inf)

        cache = collision_cache.times.setdefault(EventType.BALL_LINEAR_CUSHION, {})

        for ball in shot.balls.values():
            state = ball.state
            params = ball.params

            for cushion in shot.table.cushion_segments.linear.values():
                obj_ids = (ball.id, cushion.id)

                if obj_ids in cache:
                    continue

                if ball.state.s in const.nontranslating:
                    cache[obj_ids] = np.inf
                    continue

                dtau_E = ball_linear_cushion_collision_time(
                    rvw=state.rvw,
                    s=state.s,
                    lx=cushion.lx,
                    ly=cushion.ly,
                    l0=cushion.l0,
                    p1=cushion.p1,
                    p2=cushion.p2,
                    direction=cushion.direction,
                    mu=(params.u_s if state.s == const.sliding else params.u_r),
                    m=params.m,
                    g=params.g,
                    R=params.R,
                )

                cache[obj_ids] = shot.t + dtau_E

        obj_ids = min(cache, key=lambda k: cache[k])

        return ball_linear_cushion_collision(
            ball=shot.balls[obj_ids[0]],
            cushion=shot.table.cushion_segments.linear[obj_ids[1]],
            time=cache[obj_ids],
        )


class BallCCushionDetectionStrategy(Protocol):
    """Ball-vs-circular-cushion-segment detection models must satisfy this protocol."""

    dim: Dim

    def get_next(self, shot: System, collision_cache: CollisionCache) -> Event: ...


@attrs.define
class BallCCushionDetection:
    """Detects the next ball-vs-circular-cushion-segment collision in the system."""

    dim: Dim = attrs.field(default=Dim.TWO, init=False, repr=False)

    def get_next(self, shot: System, collision_cache: CollisionCache) -> Event:
        if not shot.table.has_circular_cushions:
            return null_event(np.inf)

        cache = collision_cache.times.setdefault(EventType.BALL_CIRCULAR_CUSHION, {})

        for ball in shot.balls.values():
            state = ball.state
            params = ball.params

            for cushion in shot.table.cushion_segments.circular.values():
                obj_ids = (ball.id, cushion.id)

                if obj_ids in cache:
                    continue

                if ball.state.s in const.nontranslating:
                    cache[obj_ids] = np.inf
                    continue

                dtau_E = ball_circular_cushion_collision_time(
                    rvw=state.rvw,
                    s=state.s,
                    a=cushion.a,
                    b=cushion.b,
                    r=cushion.radius,
                    mu=(params.u_s if state.s == const.sliding else params.u_r),
                    m=params.m,
                    g=params.g,
                    R=params.R,
                )
                cache[obj_ids] = shot.t + dtau_E

        ball_id, cushion_id = min(cache, key=lambda k: cache[k])

        return ball_circular_cushion_collision(
            ball=shot.balls[ball_id],
            cushion=shot.table.cushion_segments.circular[cushion_id],
            time=cache[(ball_id, cushion_id)],
        )
