from __future__ import annotations

import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.events import Event, EventType, ball_pocket_collision, null_event
from pooltool.evolution.event_based.cache import CollisionCache
from pooltool.physics.utils import get_airborne_time, get_u_vec
from pooltool.ptmath.roots import quadratic, quartic
from pooltool.ptmath.roots.core import get_real_positive_smallest_root
from pooltool.system.datatypes import System


@jit(nopython=True, cache=const.use_numba_cache)
def ball_pocket_collision_coeffs(
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
    """Get quartic coeffs required to determine the ball-pocket collision time

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
    E = 0.5 * (a * a + b * b + cx * cx + cy * cy - r * r) - (cx * a + cy * b)

    return A, B, C, D, E


@jit(nopython=True, cache=const.use_numba_cache)
def ball_pocket_collision_time(
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
    """Get the time until collision between a ball and a pocket."""
    return get_real_positive_smallest_root(
        quartic.solve(
            *ball_pocket_collision_coeffs(
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


@jit(nopython=True, cache=const.use_numba_cache)
def ball_pocket_collision_time_airborne(
    rvw: NDArray[np.float64],
    a: float,
    b: float,
    r: float,
    g: float,
    R: float,
) -> float:
    """Determine the ball-pocket collision time for an airborne ball.

    The behavior is somewhat complicated. Here is the procedure.

    Strategy 1: The xy-coordinates of where the ball lands are calculated. If that falls
    within the pocket circle, a collision is returned. The collision time is chosen to
    be just less than the collision time for the table collision, to guarantee temporal
    precedence over the table collision.

    Strategy 2: Otherwise, the influx and outflux collision times are calculated between
    the ball center and a vertical cylinder that extends from the pocket's circle.
    Influx collision refers to the collision with the outside of the cylinder's wall.
    The outflux collision refers to the collision with the inside of the cylinder's wall
    and occurs later in time. Since there is no deceleration in the xy-plane for an
    airborne ball, an outflux collision is expected, meaning we expect 2 finite roots.
    (This is only violated if the ball starts inside the cylinder, which results in at
    most an outflux collision). The strategy is to see what the ball height is at the
    time of the influx collision (``h0``) and the outflux collision (``hf``), because
    from these we can determine whether or not the ball is considered to enter the
    pocket. The following logic is used:

        - ``h0 < R``: The ball passes through the playing surface plane before
          intersecting the pocket cylinder, guaranteeing that a ball-table collision
          occurs. Infinity is returned.
        - ``hf <= (7/5)*R``: If the outflux height is less than ``(7/5)*R``, the ball
          is considered to be pocketed. This threshold height implicitly models the
          fact that high velocity balls that are slightly airborne collide with table
          geometry at the back of the pocket, ricocheting the ball into the pocket.
          The average of the influx and outflux collision times is returned.
        - ``hf > (7/5)*R``: The ball is considered to fly over the pocket. Infinity is
          returned.
    """
    phi = ptmath.angle(rvw[1])
    v = ptmath.norm2d(rvw[1])
    cos_phi = np.cos(phi)
    sin_phi = np.sin(phi)
    bx, by = v * cos_phi, v * sin_phi

    # Strategy 1: does the ball land inside the pocket circle?
    airborne_time = get_airborne_time(rvw, R, g)
    x = rvw[0, 0] + bx * airborne_time
    y = rvw[0, 1] + by * airborne_time

    if (x - a) ** 2 + (y - b) ** 2 < r * r:
        return float(airborne_time - const.EPS)

    # Strategy 2: does the ball's xy trajectory cross the pocket cylinder?
    cx, cy = rvw[0, 0], rvw[0, 1]

    # These match the non-airborne quartic coefficients, after setting ax=ay=0.
    C = 0.5 * (bx * bx + by * by)
    D = bx * (cx - a) + by * (cy - b)
    E = 0.5 * (a * a + b * b + cx * cx + cy * cy - r * r) - (cx * a + cy * b)

    roots = quadratic.solve(C, D, E)

    atol = 1e-9
    if abs(roots[0].imag) > atol or abs(roots[1].imag) > atol:
        return np.inf

    real_0 = roots[0].real
    real_1 = roots[1].real
    if real_0 <= real_1:
        r1, r2 = real_0, real_1
    else:
        r1, r2 = real_1, real_0

    if r1 < 0.0:
        return np.inf

    v0z = rvw[1, 2]
    z0 = rvw[0, 2]

    h0 = -0.5 * g * r1 * r1 + v0z * r1 + z0
    hf = -0.5 * g * r2 * r2 + v0z * r2 + z0

    if h0 < R:
        return np.inf

    if hf > 7.0 / 5.0 * R:
        return np.inf

    return (r1 + r2) / 2.0


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
