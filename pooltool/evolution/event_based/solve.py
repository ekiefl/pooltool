import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const
import pooltool.physics as physics
import pooltool.physics.evolve as evolve
import pooltool.ptmath as ptmath
from pooltool.physics.utils import get_airborne_time
from pooltool.ptmath.roots import quadratic, quartic
from pooltool.ptmath.roots.core import (
    filter_non_physical_roots,
)


@jit(nopython=True, cache=const.use_numba_cache)
def get_u(
    rvw: NDArray[np.float64], R: float, phi: float, s: int
) -> NDArray[np.float64]:
    if s == const.pocketed or s == const.airborne:
        raise ValueError(
            f"State {s} is not on table, so relative velocity u is not defined."
        )

    if s == const.rolling:
        return np.array([1, 0, 0], dtype=np.float64)

    rel_vel = physics.rel_velocity(rvw, R)
    if (rel_vel == 0).all():
        return np.array([1, 0, 0], dtype=np.float64)

    return ptmath.coordinate_rotation(ptmath.unit_vector(rel_vel), -phi)


@jit(nopython=True, cache=const.use_numba_cache)
def ball_ball_collision_coeffs(
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
) -> tuple[float, float, float, float, float]:
    """Get quartic coeffs required to determine the ball-ball collision time

    (just-in-time compiled)
    """

    c1x, c1y = rvw1[0, 0], rvw1[0, 1]
    c2x, c2y = rvw2[0, 0], rvw2[0, 1]

    if s1 == const.spinning or s1 == const.pocketed or s1 == const.stationary:
        a1x, a1y, b1x, b1y = 0, 0, 0, 0
    else:
        phi1 = ptmath.projected_angle(rvw1[1])
        v1 = ptmath.norm3d(rvw1[1])

        u1 = get_u(rvw1, R, phi1, s1)

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
        phi2 = ptmath.projected_angle(rvw2[1])
        v2 = ptmath.norm3d(rvw2[1])

        u2 = get_u(rvw2, R, phi2, s2)

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

    a = Ax**2 + Ay**2
    b = 2 * Ax * Bx + 2 * Ay * By
    c = Bx**2 + 2 * Ax * Cx + 2 * Ay * Cy + By**2
    d = 2 * Bx * Cx + 2 * By * Cy
    e = Cx**2 + Cy**2 - 4 * R**2

    return a, b, c, d, e


@jit(nopython=True, cache=const.use_numba_cache)
def ball_table_collision_time(
    rvw: NDArray[np.float64],
    s: int,
    g: float,
    R: float,
) -> float:
    """Get time until collision between ball and table surface."""
    if s != const.airborne:
        # Non-airborne ball cannot have a ball-table collision
        return np.inf

    return physics.get_airborne_time(rvw=rvw, R=R, g=g)


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
    """Get time until collision between ball and linear cushion segment."""
    if s == const.spinning or s == const.pocketed or s == const.stationary:
        return np.inf

    phi = ptmath.projected_angle(rvw[1])
    v = ptmath.norm2d(rvw[1])
    cos_phi = np.cos(phi)
    sin_phi = np.sin(phi)

    if s == const.airborne:
        ax = 0.0
        ay = 0.0
    else:
        u = get_u(rvw, R, phi, s)
        K = -0.5 * mu * g
        ax = K * (u[0] * cos_phi - u[1] * sin_phi)
        ay = K * (u[0] * sin_phi + u[1] * cos_phi)

    bx, by = v * cos_phi, v * sin_phi
    cx, cy = rvw[0, 0], rvw[0, 1]

    A = lx * ax + ly * ay
    B = lx * bx + ly * by

    if A == 0 and B == 0:
        # C must be 0, but whether or not it is, time is a free parameter.
        return np.inf

    roots = np.full(4, np.nan, dtype=np.complex128)

    if direction == 0:
        C = l0 + lx * cx + ly * cy + R * np.sqrt(lx**2 + ly**2)
        roots[:2] = quadratic.solve(A, B, C)
    elif direction == 1:
        C = l0 + lx * cx + ly * cy - R * np.sqrt(lx**2 + ly**2)
        roots[:2] = quadratic.solve(A, B, C)
    else:
        C1 = l0 + lx * cx + ly * cy + R * np.sqrt(lx**2 + ly**2)
        C2 = l0 + lx * cx + ly * cy - R * np.sqrt(lx**2 + ly**2)
        roots[:2] = quadratic.solve(A, B, C1)
        roots[2:] = quadratic.solve(A, B, C2)

    physical_roots = filter_non_physical_roots(roots)

    for root in physical_roots:
        if root.real == np.inf:
            continue

        # FIXME-3D, ideally any sort of determination of real versus not is determined
        # in filter_non_physical_roots. Remove this and observe behavior closely.
        if root.real <= const.EPS:
            continue

        rvw_dtau = evolve.evolve_ball_motion(s, rvw, R, m, mu, 1, mu, g, root.real)
        s_score = -np.dot(p1 - rvw_dtau[0], p2 - p1) / np.dot(p2 - p1, p2 - p1)

        if 0 <= s_score <= 1:
            return root.real

    return np.inf


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
    """Get quartic coeffs required to determine the ball-circular-cushion collision time."""

    if s == const.spinning or s == const.pocketed or s == const.stationary:
        return np.inf, np.inf, np.inf, np.inf, np.inf

    phi = ptmath.projected_angle(rvw[1])
    v = ptmath.norm2d(rvw[1])
    cos_phi = np.cos(phi)
    sin_phi = np.sin(phi)

    if s == const.airborne:
        ax = 0.0
        ay = 0.0
    else:
        u = get_u(rvw, R, phi, s)
        K = -0.5 * mu * g
        ax = K * (u[0] * cos_phi - u[1] * sin_phi)
        ay = K * (u[0] * sin_phi + u[1] * cos_phi)

    bx, by = v * cos_phi, v * sin_phi
    cx, cy = rvw[0, 0], rvw[0, 1]

    A = 0.5 * (ax**2 + ay**2)
    B = ax * bx + ay * by
    C = ax * (cx - a) + ay * (cy - b) + 0.5 * (bx**2 + by**2)
    D = bx * (cx - a) + by * (cy - b)
    E = 0.5 * (a**2 + b**2 + cx**2 + cy**2 - (r + R) ** 2) - (cx * a + cy * b)

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
    """Determine the ball-pocket collision time.

    The behavior for airborne versus non-airborne state is treated differently. This
    function delegates to :func:`ball_pocket_collision_time_airborne` when the state is
    airborne.
    """

    if s == const.spinning or s == const.pocketed or s == const.stationary:
        return np.inf

    if s == const.airborne:
        return ball_pocket_collision_time_airborne(rvw, a, b, r, g, R)

    phi = ptmath.projected_angle(rvw[1])
    v = ptmath.norm2d(rvw[1])
    cos_phi = np.cos(phi)
    sin_phi = np.sin(phi)

    u = get_u(rvw, R, phi, s)
    K = -0.5 * mu * g
    ax = K * (u[0] * cos_phi - u[1] * sin_phi)
    ay = K * (u[0] * sin_phi + u[1] * cos_phi)

    bx, by = v * cos_phi, v * sin_phi
    cx, cy = rvw[0, 0], rvw[0, 1]

    A = 0.5 * (ax**2 + ay**2)
    B = ax * bx + ay * by
    C = ax * (cx - a) + ay * (cy - b) + 0.5 * (bx**2 + by**2)
    D = bx * (cx - a) + by * (cy - b)
    E = 0.5 * (a**2 + b**2 + cx**2 + cy**2 - r**2) - (cx * a + cy * b)

    roots = quartic.solve(A, B, C, D, E)
    return filter_non_physical_roots(roots)[0].real


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
    time of the influx collision (h0) and the outflux collision (hf), because from these
    we can determine whether or not the ball is considered to enter the pocket. The
    following logic is used:

        - h0 < R: The ball passes through the playing surface plane before intersecting
          the pocket cylinder, guaranteeing that a ball-table collision occurs. Infinity
          is returned.
        - hf <= (7/5)*R: If the outflux height is less than (7/5)*R, the ball is
          considered to be pocketed. This threshold height implicitly models the fact
          that high velocity balls that are slightly airborne collide with table
          geometry at the back of the pocket, ricocheting the ball into the pocket. The
          average of the influx and outflux collision times is returned.
        - hf > (7/5)*R: The ball is considered to fly over the pocket. Infinity is
          returned.
    """

    phi = ptmath.projected_angle(rvw[1])
    v = ptmath.norm2d(rvw[1])
    cos_phi = np.cos(phi)
    sin_phi = np.sin(phi)
    bx, by = v * cos_phi, v * sin_phi

    # Strategy 1

    airborne_time = get_airborne_time(rvw, R, g)
    x = rvw[0, 0] + bx * airborne_time
    y = rvw[0, 1] + by * airborne_time

    if (x - a) ** 2 + (y - b) ** 2 < r**2:
        # The ball falls directly into the pocket
        return float(airborne_time - const.EPS)

    # Strategy 2

    cx, cy = rvw[0, 0], rvw[0, 1]

    # These match the non-airborne quartic coefficients, after setting ax=ay=0.
    C = 0.5 * (bx**2 + by**2)
    D = bx * (cx - a) + by * (cy - b)
    E = 0.5 * (a**2 + b**2 + cx**2 + cy**2 - r**2) - (cx * a + cy * b)

    r1, r2 = filter_non_physical_roots(quadratic.solve(C, D, E)).real

    if r1 == np.inf:
        return r1

    assert r2 != np.inf, "Expected finite out-flux collision with pocket"

    v0z = rvw[1, 2]
    z0 = rvw[0, 2]

    # Height at influx collision and height at outflux collision
    h0 = -0.5 * g * r1**2 + v0z * r1 + z0
    hf = -0.5 * g * r2**2 + v0z * r1 + z0

    if h0 < R:
        # Ball hits table before reaching pocket. Safe to return inf
        assert hf < h0
        return np.inf

    thresh = 7 / 5 * R
    if hf > thresh:
        # Ball flies over pocket
        return np.inf

    # Return average time of influx/outflux collisions
    return (r1 + r2) / 2.0
