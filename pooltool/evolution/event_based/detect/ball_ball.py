from __future__ import annotations

from itertools import combinations

import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.events import Event, EventType, ball_ball_collision, null_event
from pooltool.evolution.event_based.cache import CollisionCache
from pooltool.evolution.event_based.detect.ball_position_polynomial import (
    ball_position_polynomial,
)
from pooltool.evolution.event_based.detect.quartic_coefficients import (
    parabola_sphere_distance_quartic_coefficients,
)
from pooltool.physics.utils import get_u_vec
from pooltool.ptmath.roots import quadratic, quartic
from pooltool.ptmath.roots.core import get_real_positive_smallest_root
from pooltool.system.datatypes import Ball, System


def ball_ball_collision_time_3d(
    ball1: Ball,
    ball2: Ball,
) -> float:
    """Get the time until collision between two balls."""
    p1: NDArray[np.float64] = ball_position_polynomial(
        ball1.state.s,
        ball1.state.rvw,
        ball1.params.R,
        ball1.params.u_r,
        ball1.params.u_s,
        ball1.params.g,
    )
    p2: NDArray[np.float64] = ball_position_polynomial(
        ball2.state.s,
        ball2.state.rvw,
        ball2.params.R,
        ball2.params.u_r,
        ball2.params.u_s,
        ball2.params.g,
    )

    p12: NDArray[np.float64] = p1 - p2

    C: NDArray[np.float64] = parabola_sphere_distance_quartic_coefficients(
        p12.T, ball1.params.R + ball2.params.R
    )

    # FIXME: quartic solver can't handle cubics or quadratics, so checking for quadratic here
    if np.isclose(C[4], 0.0):
        # C[3] must also be 0.0, and this is a quadratic
        assert np.isclose(C[3], 0.0)
        return get_real_positive_smallest_root(quadratic.solve(C[2], C[1], C[0]))

    return get_real_positive_smallest_root(quartic.solve(C[4], C[3], C[2], C[1], C[0]))


@jit(nopython=True, cache=const.use_numba_cache)
def ball_ball_collision_time_2d(
    rvw1: NDArray[np.float64],
    rvw2: NDArray[np.float64],
    s1: int,
    s2: int,
    mu1: float,
    mu2: float,
    m1: float,
    m2: float,
    g1: float,
    g2: float,
    R: float,
) -> float:
    """Get the time until collision between two balls.

    Note:
        - TODO(Evan) This is a legacy function used for detecting ball-ball collisions
          under the assumption of 2D (on-table) trajectories. It's behavior is in theory
          superseded by :func:`ball_ball_collision_time`, however remains in production
          until it can be proven that :func:`ball_ball_collision` treats 2D trajectories
          identically.
    """
    c1x, c1y = rvw1[0, 0], rvw1[0, 1]
    c2x, c2y = rvw2[0, 0], rvw2[0, 1]

    if s1 == const.spinning or s1 == const.pocketed or s1 == const.stationary:
        a1x, a1y, b1x, b1y = 0, 0, 0, 0
    else:
        phi1 = ptmath.angle(rvw1[1])
        v1 = ptmath.norm3d(rvw1[1])

        u1 = get_u_vec(rvw1, R, phi1, s1)

        K1 = -0.5 * mu1 * g1
        cos_phi1 = np.cos(phi1)
        sin_phi1 = np.sin(phi1)

        a1x = K1 * (u1[0] * cos_phi1 - u1[1] * sin_phi1)
        a1y = K1 * (u1[0] * sin_phi1 + u1[1] * cos_phi1)
        b1x = v1 * cos_phi1
        b1y = v1 * sin_phi1

    if s2 == const.spinning or s2 == const.pocketed or s2 == const.stationary:
        a2x, a2y, b2x, b2y = 0.0, 0.0, 0.0, 0.0
    else:
        phi2 = ptmath.angle(rvw2[1])
        v2 = ptmath.norm3d(rvw2[1])

        u2 = get_u_vec(rvw2, R, phi2, s2)

        K2 = -0.5 * mu2 * g2
        cos_phi2 = np.cos(phi2)
        sin_phi2 = np.sin(phi2)

        a2x = K2 * (u2[0] * cos_phi2 - u2[1] * sin_phi2)
        a2y = K2 * (u2[0] * sin_phi2 + u2[1] * cos_phi2)
        b2x = v2 * cos_phi2
        b2y = v2 * sin_phi2

    Ax, Ay = a2x - a1x, a2y - a1y
    Bx, By = b2x - b1x, b2y - b1y
    Cx, Cy = c2x - c1x, c2y - c1y

    a = Ax * Ax + Ay * Ay
    b = 2 * Ax * Bx + 2 * Ay * By
    c = Bx * Bx + 2 * Ax * Cx + 2 * Ay * Cy + By * By
    d = 2 * Bx * Cx + 2 * By * Cy
    e = Cx * Cx + Cy * Cy - 4 * R * R

    return get_real_positive_smallest_root(quartic.solve(a, b, c, d, e))


def get_next_ball_ball_event(
    shot: System, collision_cache: CollisionCache, *, is_3d: bool
) -> Event:
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
            if is_3d:
                dtau_E = ball_ball_collision_time_3d(ball1, ball2)
            else:
                dtau_E = ball_ball_collision_time_2d(
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
