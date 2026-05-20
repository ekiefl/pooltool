from __future__ import annotations

import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const
import pooltool.physics.evolve as evolve
import pooltool.ptmath as ptmath
from pooltool.events import (
    Event,
    EventType,
    ball_circular_cushion_collision,
    ball_linear_cushion_collision,
    null_event,
)
from pooltool.evolution.event_based.cache import CollisionCache
from pooltool.physics.utils import get_u_vec
from pooltool.ptmath.roots import quartic
from pooltool.ptmath.roots.core import get_real_positive_smallest_root
from pooltool.system.datatypes import System


@jit(nopython=True, cache=const.use_numba_cache)
def ball_linear_cushion_collision_time(
    rvw: NDArray[np.float64],
    s: int,
    lx: float,
    ly: float,
    l0: float,
    p1: NDArray[np.float64],
    p2: NDArray[np.float64],
    direction: int,
    mu: float,
    m: float,
    g: float,
    R: float,
) -> float:
    """Get time until collision between ball and linear cushion segment

    (just-in-time compiled)
    """
    if s == const.spinning or s == const.pocketed or s == const.stationary:
        return np.inf

    phi = ptmath.angle(rvw[1])
    v = ptmath.norm3d(rvw[1])

    u = get_u_vec(rvw, R, phi, s)

    K = -0.5 * mu * g
    cos_phi = np.cos(phi)
    sin_phi = np.sin(phi)

    ax = K * (u[0] * cos_phi - u[1] * sin_phi)
    ay = K * (u[0] * sin_phi + u[1] * cos_phi)
    bx, by = v * cos_phi, v * sin_phi
    cx, cy = rvw[0, 0], rvw[0, 1]

    A = lx * ax + ly * ay
    B = lx * bx + ly * by

    if direction == 0:
        C = l0 + lx * cx + ly * cy + R * np.sqrt(lx * lx + ly * ly)
        root1, root2 = ptmath.roots.quadratic.solve(A, B, C)
        roots = [root1, root2]
    elif direction == 1:
        C = l0 + lx * cx + ly * cy - R * np.sqrt(lx * lx + ly * ly)
        root1, root2 = ptmath.roots.quadratic.solve(A, B, C)
        roots = [root1, root2]
    else:
        C1 = l0 + lx * cx + ly * cy + R * np.sqrt(lx * lx + ly * ly)
        C2 = l0 + lx * cx + ly * cy - R * np.sqrt(lx * lx + ly * ly)
        root1, root2 = ptmath.roots.quadratic.solve(A, B, C1)
        root3, root4 = ptmath.roots.quadratic.solve(A, B, C2)
        roots = [root1, root2, root3, root4]

    min_time = np.inf
    for root in roots:
        if np.isnan(root):
            continue

        if np.abs(root.imag) > const.EPS:
            continue

        if root.real <= const.EPS:
            continue

        rvw_dtau, _ = evolve.evolve_ball_motion(s, rvw, R, m, mu, 1, mu, g, root.real)
        s_score = -np.dot(p1 - rvw_dtau[0], p2 - p1) / np.dot(p2 - p1, p2 - p1)

        if not (0 <= s_score <= 1):
            continue

        if root.real < min_time:
            min_time = root.real

    return min_time


@jit(nopython=True, cache=const.use_numba_cache)
def ball_circular_cushion_collision_coeffs(
    rvw: NDArray[np.float64],
    s: int,
    a: float,
    b: float,
    r: float,
    mu: float,
    m: float,
    g: float,
    R: float,
) -> tuple[float, float, float, float, float]:
    """Get quartic coeffs required to determine the ball-circular-cushion collision time

    (just-in-time compiled)
    """

    if s == const.spinning or s == const.pocketed or s == const.stationary:
        return np.inf, np.inf, np.inf, np.inf, np.inf

    phi = ptmath.angle(rvw[1])
    v = ptmath.norm3d(rvw[1])

    u = get_u_vec(rvw, R, phi, s)

    K = -0.5 * mu * g
    cos_phi = np.cos(phi)
    sin_phi = np.sin(phi)

    ax = K * (u[0] * cos_phi - u[1] * sin_phi)
    ay = K * (u[0] * sin_phi + u[1] * cos_phi)
    bx, by = v * cos_phi, v * sin_phi
    cx, cy = rvw[0, 0], rvw[0, 1]

    A = 0.5 * (ax * ax + ay * ay)
    B = ax * bx + ay * by
    C = ax * (cx - a) + ay * (cy - b) + 0.5 * (bx * bx + by * by)
    D = bx * (cx - a) + by * (cy - b)
    E = 0.5 * (a * a + b * b + cx * cx + cy * cy - (r + R) * (r + R)) - (
        cx * a + cy * b
    )

    return A, B, C, D, E


@jit(nopython=True, cache=const.use_numba_cache)
def ball_circular_cushion_collision_time(
    rvw: NDArray[np.float64],
    s: int,
    a: float,
    b: float,
    r: float,
    mu: float,
    m: float,
    g: float,
    R: float,
) -> float:
    """Get the time until collision between a ball and a circular cushion segment."""
    return get_real_positive_smallest_root(
        quartic.solve(
            *ball_circular_cushion_collision_coeffs(
                rvw,
                s,
                a,
                b,
                r,
                mu,
                m,
                g,
                R,
            )
        )
    )


def get_next_ball_linear_cushion_2d_event(
    shot: System, collision_cache: CollisionCache
) -> Event:
    """Detect the next ball-vs-linear-cushion collision in 2D mode."""
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


def get_next_ball_linear_cushion_3d_event(
    shot: System, collision_cache: CollisionCache
) -> Event:
    """3D ball-linear-cushion detection — not vendored yet; emits no event."""
    return null_event(np.inf)


def get_next_ball_circular_cushion_2d_event(
    shot: System, collision_cache: CollisionCache
) -> Event:
    """Detect the next ball-vs-circular-cushion collision in 2D mode."""
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


def get_next_ball_circular_cushion_3d_event(
    shot: System, collision_cache: CollisionCache
) -> Event:
    return null_event(np.inf)
