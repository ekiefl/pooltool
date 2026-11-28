"""Contact time between a parabolic trajectory and a torus.

The nose of a circular cushion segment is a torus: a horizontal nose circle of
radius ``r`` wrapped in a tube of radius ``nose_radius``. A ball of radius ``R``
touches it when its center is a distance ``D = R + nose_radius`` from the nose
circle. For an
airborne ball the center follows a parabola, and the exact contact condition is a
degree-eight polynomial in time, which is too expensive to solve per ball-cushion
pair. This module instead solves a short sequence of quartics.

Write the squared distance from the center to the nose circle, minus ``D**2``, as

    g(t) = [rho**2 + z**2 + r**2 - D**2] - 2 r rho

where ``rho`` is the horizontal distance from the torus axis and ``z`` the height
above the nose circle. The bracket is a quartic in ``t`` because ``rho**2`` and
``z**2`` are; only the lone ``rho`` is not polynomial. For any ``c > 0`` the bound
``rho <= (rho**2 + c**2) / (2 c)`` is exact where ``rho = c``, and substituting it
gives the quartic

    g_c(t) = (1 - r / c) rho**2 + z**2 + r**2 - D**2 - r c  <=  g(t)

whose zero set is a spheroid (``c > r``) or hyperboloid (``c < r``) of revolution
enclosing the torus and tangent to it along the parallel ``rho = c``. Because
``g_c`` never exceeds ``g``, the first root of ``g_c`` after ``t_k`` is never later
than the first root of ``g``. Setting ``c`` to the ball's ``rho`` at ``t_k``, solving,
moving to the root and repeating therefore walks up to the true contact
monotonically and stops there, since a fixed point has ``g_c = g``. No root is a
certificate of no contact. A prefilter on the bounding cylinder ``rho <= r + D`` and
height band ``|z| <= D`` bounds the search and rejects most pairs with two
quadratics.
"""

import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const
from pooltool.ptmath.roots import (
    ABS_OR_REL_CUTOFF,
    ATOL,
    RTOL,
    is_real_number,
    quartic,
)

MAX_SOLVES = 80
RESIDUAL_TOL = 1e-14
C_FLOOR = 1e-9


@jit(nopython=True, cache=const.use_numba_cache)
def torus_contact_windows(
    X0: float,
    Y0: float,
    Z0: float,
    vx: float,
    vy: float,
    vz: float,
    g: float,
    r: float,
    D: float,
) -> tuple[int, float, float, float, float]:
    """Time intervals in which the trajectory can be within ``D`` of the nose circle.

    The intervals are the intersection of the bounding vertical cylinder of radius
    ``r + D``, the height band ``|z| <= D`` and ``t >= 0``. Positions are relative to
    the torus center. Returns ``(count, lo0, hi0, lo1, hi1)`` with at most two
    intervals; unused entries are ``np.inf``.
    """
    alpha = vx * vx + vy * vy
    beta = 2.0 * (X0 * vx + Y0 * vy)
    gamma = X0 * X0 + Y0 * Y0 - (r + D) ** 2

    if alpha < 1e-14:
        if gamma > 0.0:
            return 0, np.inf, np.inf, np.inf, np.inf
        tc1, tc2 = 0.0, np.inf
    else:
        disc = beta * beta - 4.0 * alpha * gamma
        if disc < 0.0:
            return 0, np.inf, np.inf, np.inf, np.inf
        sd = np.sqrt(disc)
        tc1 = (-beta - sd) / (2.0 * alpha)
        tc2 = (-beta + sd) / (2.0 * alpha)

    disc_lo = vz * vz + 2.0 * g * (Z0 + D)
    if disc_lo < 0.0:
        return 0, np.inf, np.inf, np.inf, np.inf
    sd_lo = np.sqrt(disc_lo)
    tb1 = (vz - sd_lo) / g
    tb2 = (vz + sd_lo) / g

    disc_hi = vz * vz + 2.0 * g * (Z0 - D)
    if disc_hi < 0.0:
        lo = max(tb1, tc1, 0.0)
        hi = min(tb2, tc2)
        if lo < hi:
            return 1, lo, hi, np.inf, np.inf
        return 0, np.inf, np.inf, np.inf, np.inf

    sd_hi = np.sqrt(disc_hi)
    ta1 = (vz - sd_hi) / g
    ta2 = (vz + sd_hi) / g

    n = 0
    lo0, hi0, lo1, hi1 = np.inf, np.inf, np.inf, np.inf
    lo = max(tb1, tc1, 0.0)
    hi = min(ta1, tc2)
    if lo < hi:
        lo0, hi0 = lo, hi
        n = 1
    lo = max(ta2, tc1, 0.0)
    hi = min(tb2, tc2)
    if lo < hi:
        if n == 0:
            lo0, hi0 = lo, hi
        else:
            lo1, hi1 = lo, hi
        n += 1
    return n, lo0, hi0, lo1, hi1


@jit(nopython=True, cache=const.use_numba_cache)
def torus_residual(
    t: float,
    X0: float,
    Y0: float,
    Z0: float,
    vx: float,
    vy: float,
    vz: float,
    g: float,
    r: float,
    D: float,
) -> float:
    """``(distance from the center to the nose circle)**2 - D**2`` at time ``t``.

    Positive means clear of the cushion, zero means touching.
    """
    X = X0 + vx * t
    Y = Y0 + vy * t
    Z = Z0 + vz * t - 0.5 * g * t * t
    rho = np.sqrt(X * X + Y * Y)
    return (rho - r) ** 2 + Z * Z - D * D


@jit(nopython=True, cache=const.use_numba_cache)
def _first_entry_root(
    a0: float, a1: float, a2: float, a3: float, a4: float, t_min: float
) -> float:
    """Smallest real root at or after ``t_min`` where the quartic is non-increasing."""
    roots = quartic.solve(a4, a3, a2, a1, a0)
    best = np.inf
    for i in range(4):
        root = roots[i]
        if not is_real_number(root, ABS_OR_REL_CUTOFF, RTOL, ATOL):
            continue
        t = root.real
        if t < t_min - 1e-12 or t >= best:
            continue
        slope = a1 + 2.0 * a2 * t + 3.0 * a3 * t * t + 4.0 * a4 * t * t * t
        if slope > 0.0:
            continue
        best = t
    return best


@jit(nopython=True, cache=const.use_numba_cache)
def _contact_time_in_window(
    lo: float,
    hi: float,
    X0: float,
    Y0: float,
    Z0: float,
    vx: float,
    vy: float,
    vz: float,
    g: float,
    r: float,
    D: float,
) -> float:
    """Enclosing-quadric iteration inside one window, see the module docstring."""
    alpha = vx * vx + vy * vy
    beta = 2.0 * (X0 * vx + Y0 * vy)
    gamma = X0 * X0 + Y0 * Y0
    z0 = Z0 * Z0
    z1 = 2.0 * Z0 * vz
    z2 = vz * vz - g * Z0
    z3 = -g * vz
    z4 = 0.25 * g * g
    offset = r * r - D * D

    t_k = lo
    for _ in range(MAX_SOLVES):
        X = X0 + vx * t_k
        Y = Y0 + vy * t_k
        c = np.sqrt(X * X + Y * Y)
        c = max(c, C_FLOOR)
        k = 1.0 - r / c
        t_next = _first_entry_root(
            z0 + k * gamma + offset - r * c, z1 + k * beta, z2 + k * alpha, z3, z4, t_k
        )
        if t_next == np.inf or t_next > hi + 1e-9:
            return np.inf
        if torus_residual(t_next, X0, Y0, Z0, vx, vy, vz, g, r, D) <= RESIDUAL_TOL:
            return t_next
        t_k = t_next
    return t_k


@jit(nopython=True, cache=const.use_numba_cache)
def _half_line(f0: float, f1: float) -> tuple[float, float]:
    """The interval of ``t`` on which ``f0 + f1 t >= 0``; empty is ``(inf, -inf)``."""
    if f1 > 0.0:
        return -f0 / f1, np.inf
    if f1 < 0.0:
        return -np.inf, -f0 / f1
    if f0 >= 0.0:
        return -np.inf, np.inf
    return np.inf, -np.inf


@jit(nopython=True, cache=const.use_numba_cache)
def _wedge_interval(
    X0: float, Y0: float, vx: float, vy: float, start: float, span: float
) -> tuple[float, float]:
    """Times at which the horizontal path lies in a wedge of at most a half turn.

    The wedge opens counterclockwise from azimuth ``start`` through ``span``. It is
    the intersection of two half-planes, counterclockwise of the start ray and
    clockwise of the end ray, and a straight path crosses each boundary at most once.
    """
    cs, ss = np.cos(start), np.sin(start)
    ce, se = np.cos(start + span), np.sin(start + span)
    lo_s, hi_s = _half_line(cs * Y0 - ss * X0, cs * vy - ss * vx)
    lo_e, hi_e = _half_line(se * X0 - ce * Y0, se * vx - ce * vy)
    return max(lo_s, lo_e), min(hi_s, hi_e)


@jit(nopython=True, cache=const.use_numba_cache)
def arc_intervals(
    X0: float, Y0: float, vx: float, vy: float, arc_start: float, arc_span: float
) -> tuple[int, float, float, float, float]:
    """Time intervals in which the horizontal path has an azimuth on the arc.

    An arc of at most a half turn is a convex wedge, which a straight path occupies
    for one interval. A wider arc has a convex complement, so the path is on the arc
    except for one interval, giving up to two. The whole ring gives one unbounded
    interval. Returns ``(count, lo0, hi0, lo1, hi1)``; unused entries are ``np.inf``.
    """
    if arc_span >= 2.0 * np.pi:
        return 1, -np.inf, np.inf, np.inf, np.inf
    if arc_span <= np.pi:
        lo, hi = _wedge_interval(X0, Y0, vx, vy, arc_start, arc_span)
        if lo < hi:
            return 1, lo, hi, np.inf, np.inf
        return 0, np.inf, np.inf, np.inf, np.inf
    lo, hi = _wedge_interval(
        X0, Y0, vx, vy, arc_start + arc_span, 2.0 * np.pi - arc_span
    )
    if lo >= hi:
        return 1, -np.inf, np.inf, np.inf, np.inf
    if lo == -np.inf:
        return 1, hi, np.inf, np.inf, np.inf
    if hi == np.inf:
        return 1, -np.inf, lo, np.inf, np.inf
    return 2, -np.inf, lo, hi, np.inf


@jit(nopython=True, cache=const.use_numba_cache)
def parabola_torus_contact_time(
    p0: NDArray[np.float64],
    v: NDArray[np.float64],
    g: float,
    r: float,
    D: float,
) -> float:
    """Time until a parabolic trajectory first comes within ``D`` of the nose circle.

    The trajectory is ``p0 + v t - (g / 2) t**2 z_hat`` with ``p0`` relative to the
    torus center, whose nose circle of radius ``r`` lies in the plane ``z = 0``. Only
    approaching contacts count, so a center already within ``D`` and moving away is
    not reported. Returns ``np.inf`` when there is no contact.
    """
    X0, Y0, Z0 = p0[0], p0[1], p0[2]
    vx, vy, vz = v[0], v[1], v[2]
    n, lo0, hi0, lo1, hi1 = torus_contact_windows(X0, Y0, Z0, vx, vy, vz, g, r, D)
    if n == 0:
        return np.inf
    t = _contact_time_in_window(lo0, hi0, X0, Y0, Z0, vx, vy, vz, g, r, D)
    if t < np.inf or n == 1:
        return t
    return _contact_time_in_window(lo1, hi1, X0, Y0, Z0, vx, vy, vz, g, r, D)
