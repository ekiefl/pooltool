from __future__ import annotations

from math import sqrt

import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const
from pooltool.events import Event, EventType, ball_off_table_collision
from pooltool.evolution.event_based.cache import CollisionCache
from pooltool.objects.table.datatypes import Table
from pooltool.physics.utils import get_airborne_time
from pooltool.system.datatypes import System


@jit(nopython=True, cache=const.use_numba_cache)
def ball_off_table_time(
    rvw: NDArray[np.float64],
    s: int,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    pocket_a: NDArray[np.float64],
    pocket_b: NDArray[np.float64],
    pocket_r: NDArray[np.float64],
    R: float,
    g: float,
) -> float:
    """Time until an airborne ball collides with the off-table boundary.

    The boundary is the edge of the playing surface, opened at the pockets. The ball
    leaves the table when its center crosses an edge, unless its flight carries it
    into a pocket, in which case it leaves the table when it flies out the far side
    of the pocket instead. Both parts of that are cheap because an airborne ball has
    no horizontal acceleration: seen from above, its track is a straight line
    ``p(t) = (x, y) + (vx, vy) t``.

    Edges: for each edge the ball moves toward, the crossing is a linear solve, e.g.
    ``t = (x_min - x) / vx`` when ``vx < 0``. The soonest crossing is ``t_edge``,
    clamped at zero for a ball that is already outside and moving away.

    Pockets: a pocket is a circle of center ``(a, b)`` and radius ``r``, and a line
    crosses a circle at the roots of a quadratic. With ``d = (x - a, y - b)``,

        ``(v . v) t^2 + 2 (d . v) t + (d . d - r^2) = 0``

    gives the entry and exit times ``t_in <= t_out``. A pocket only matters if the
    ball actually passes through it on its way off the table: the ball must still
    be short of the pocket when it crosses the edge (``t_out > t_edge``) and must
    reach it before landing (``t_in <= t_land``). Then the ball leaves the table at
    ``t_out`` rather than ``t_edge``. A pocket the track misses, one the ball has
    already flown past, or one it would only reach after landing changes nothing.
    A pocket in the interior of the playing surface is always one the ball has
    already flown past by the time it reaches an edge, so it never opens the
    boundary.

    This function knows nothing about pocketing. A ball that lands or dips into the
    pocket while inside the circle is still assigned its circle-exit time here; the
    pocket detector reports an earlier time for it, and if the two coincide the
    event priority in :mod:`pooltool.evolution.event_based.detect.detector` ranks
    the pocket event first.

    Returns ``np.inf`` if the ball is not airborne or has no horizontal velocity
    toward any edge.
    """
    if s != const.airborne:
        return np.inf

    x, y = rvw[0, 0], rvw[0, 1]
    vx, vy = rvw[1, 0], rvw[1, 1]

    t_edge = np.inf
    if vx < 0.0:
        t_edge = min(t_edge, (x_min - x) / vx)
    elif vx > 0.0:
        t_edge = min(t_edge, (x_max - x) / vx)
    if vy < 0.0:
        t_edge = min(t_edge, (y_min - y) / vy)
    elif vy > 0.0:
        t_edge = min(t_edge, (y_max - y) / vy)

    if t_edge == np.inf:
        return np.inf

    t_edge = max(t_edge, 0.0)
    t_land = get_airborne_time(rvw, R, g)

    A = vx * vx + vy * vy
    t_off = t_edge
    for i in range(pocket_a.shape[0]):
        px = x - pocket_a[i]
        py = y - pocket_b[i]
        B = 2.0 * (px * vx + py * vy)
        C = px * px + py * py - pocket_r[i] * pocket_r[i]
        disc = B * B - 4.0 * A * C
        if disc <= 0.0:
            continue
        root = sqrt(disc)
        t_in = (-B - root) / (2.0 * A)
        t_out = (-B + root) / (2.0 * A)
        if t_out <= t_edge or t_in > t_land:
            continue
        t_off = max(t_off, t_out)

    return t_off


def off_table_bounds(table: Table) -> tuple[float, float, float, float]:
    """The horizontal bounds beyond which an airborne ball is off the table.

    The playing surface spans ``[0, w] x [0, l]`` and the cushion nose axes lie along
    its edges, so the bounds are the vertical planes through those axes. Once the
    ball's center is past a plane, the normal of any contact with that cushion's nose
    points away from the table, so the ball cannot be turned back.

    Returns:
        ``(x_min, x_max, y_min, y_max)``.
    """
    return 0.0, table.w, 0.0, table.l


def pocket_circles(
    table: Table,
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """The pocket centers and radii as arrays ``(a, b, r)``, for the jitted solver."""
    pockets = list(table.pockets.values())
    a = np.array([pocket.a for pocket in pockets], dtype=np.float64)
    b = np.array([pocket.b for pocket in pockets], dtype=np.float64)
    r = np.array([pocket.radius for pocket in pockets], dtype=np.float64)
    return a, b, r


def get_next_ball_off_table_event(
    shot: System, collision_cache: CollisionCache
) -> Event:
    """Detect the next airborne ball leaving the table.

    Only invoked when ``EventDetector.is_3d`` is True, since only airborne balls can
    leave the table.
    """
    cache = collision_cache.times.setdefault(EventType.BALL_OFF_TABLE, {})

    stale = [ball for ball in shot.balls.values() if (ball.id,) not in cache]
    if stale:
        x_min, x_max, y_min, y_max = off_table_bounds(shot.table)
        pocket_a, pocket_b, pocket_r = pocket_circles(shot.table)

        for ball in stale:
            dtau_E = ball_off_table_time(
                ball.state.rvw,
                ball.state.s,
                x_min,
                x_max,
                y_min,
                y_max,
                pocket_a,
                pocket_b,
                pocket_r,
                ball.params.R,
                ball.params.g,
            )
            cache[(ball.id,)] = shot.t + dtau_E

    obj_ids = min(cache, key=lambda k: cache[k])

    return ball_off_table_collision(
        ball=shot.balls[obj_ids[0]],
        time=cache[obj_ids],
    )
