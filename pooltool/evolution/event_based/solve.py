from math import acos
from typing import Tuple

import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const
import pooltool.physics.evolve as evolve
import pooltool.ptmath as ptmath


@jit(nopython=True, cache=const.use_numba_cache)
def skip_ball_ball_collision(
    rvw1: NDArray[np.float64],
    rvw2: NDArray[np.float64],
    s1: int,
    s2: int,
    R1: float,
    R2: float,
) -> bool:
    if (s1 == const.spinning or s1 == const.pocketed or s1 == const.stationary) and (
        s2 == const.spinning or s2 == const.pocketed or s2 == const.stationary
    ):
        # Neither balls are moving. No collision.
        return True

    if s1 == const.pocketed or s2 == const.pocketed:
        # One of the balls is pocketed
        return True

    if s1 == const.rolling and s2 == const.rolling:
        # Both balls are rolling (straight line trajectories). Here I am checking
        # whether both dot products face away from the line connecting the two balls. If
        # so, they are guaranteed not to collide
        r12 = rvw2[0] - rvw1[0]
        dot1 = r12[0] * rvw1[1, 0] + r12[1] * rvw1[1, 1] + r12[2] * rvw1[1, 2]
        if dot1 <= 0:
            dot2 = r12[0] * rvw2[1, 0] + r12[1] * rvw2[1, 1] + r12[2] * rvw2[1, 2]
            if dot2 >= 0:
                return True

    if s1 == const.rolling and (s2 == const.spinning or s2 == const.stationary):
        # ball1 is rolling, which guarantees a straight-line trajectory. Some
        # assumptions can be made based on this fact
        r12 = rvw2[0] - rvw1[0]

        # ball2 is not moving, so we can pinpoint the range of angles ball1 must be
        # headed in for a collision
        d = ptmath.norm3d(r12)
        unit_d = r12 / d
        unit_v = ptmath.unit_vector(rvw1[1])

        # Angles are in radians
        # Calculate forwards and backwards angles, e.g. 10 and 350, take the min
        angle = np.arccos(np.dot(unit_d, unit_v))
        max_hit_angle = 0.5 * np.pi - acos((R1 + R2) / d)
        if angle > max_hit_angle:
            return True

    if s2 == const.rolling and (s1 == const.spinning or s1 == const.stationary):
        # ball2 is rolling, which guarantees a straight-line trajectory. Some
        # assumptions can be made based on this fact
        r21 = rvw1[0] - rvw2[0]

        # ball1 is not moving, so we can pinpoint the range of angles ball2 must be
        # headed in for a collision
        d = ptmath.norm3d(r21)
        unit_d = r21 / d
        unit_v = ptmath.unit_vector(rvw2[1])

        # Angles are in radians
        # Calculate forwards and backwards angles, e.g. 10 and 350, take the min
        angle = np.arccos(np.dot(unit_d, unit_v))
        max_hit_angle = 0.5 * np.pi - acos((R1 + R2) / d)
        if angle > max_hit_angle:
            return True

    return False


@jit(nopython=True, cache=const.use_numba_cache)
def get_u(
    rvw: NDArray[np.float64], R: float, phi: float, s: int
) -> NDArray[np.float64]:
    if s == const.rolling:
        return np.array([1, 0, 0], dtype=np.float64)

    rel_vel = ptmath.rel_velocity(rvw, R)
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
) -> Tuple[float, float, float, float, float]:
    """Get quartic coeffs required to determine the ball-ball collision time

    (just-in-time compiled)
    """

    c1x, c1y = rvw1[0, 0], rvw1[0, 1]
    c2x, c2y = rvw2[0, 0], rvw2[0, 1]

    if s1 == const.spinning or s1 == const.pocketed or s1 == const.stationary:
        a1x, a1y, b1x, b1y = 0, 0, 0, 0
    else:
        phi1 = ptmath.angle(rvw1[1])
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
        phi2 = ptmath.angle(rvw2[1])
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


def ball_ball_collision_time(
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
    """Get the time until collision between 2 balls

    NOTE This is deprecated. Rather than solve the roots of a single polynomial
    equation, as is done in this function, all roots of a given collision class are
    solved simultaneously via ptmath.roots
    """
    a, b, c, d, e = ball_ball_collision_coeffs(
        rvw1, rvw2, s1, s2, mu1, mu2, m1, m2, g1, g2, R
    )
    roots = np.roots([a, b, c, d, e])

    roots = roots[(abs(roots.imag) <= const.EPS) & (roots.real > const.EPS)].real

    return roots.min() if len(roots) else np.inf


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

    u = get_u(rvw, R, phi, s)

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
        C = l0 + lx * cx + ly * cy + R * np.sqrt(lx**2 + ly**2)
        root1, root2 = ptmath.roots.quadratic.solve(A, B, C)
        roots = [root1, root2]
    elif direction == 1:
        C = l0 + lx * cx + ly * cy - R * np.sqrt(lx**2 + ly**2)
        root1, root2 = ptmath.roots.quadratic.solve(A, B, C)
        roots = [root1, root2]
    else:
        C1 = l0 + lx * cx + ly * cy + R * np.sqrt(lx**2 + ly**2)
        C2 = l0 + lx * cx + ly * cy - R * np.sqrt(lx**2 + ly**2)
        root1, root2 = ptmath.roots.quadratic.solve(A, B, C1)
        root3, root4 = ptmath.roots.quadratic.solve(A, B, C2)
        roots = [root1, root2, root3, root4]

    min_time = np.inf
    for root in roots:
        if np.abs(root.imag) > const.EPS:
            continue

        if root.real <= const.EPS:
            continue

        rvw_dtau, _ = evolve.evolve_ball_motion(s, rvw, R, m, mu, 1, mu, g, root)
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
) -> Tuple[float, float, float, float, float]:
    """Get quartic coeffs required to determine the ball-circular-cushion collision time

    (just-in-time compiled)
    """

    if s == const.spinning or s == const.pocketed or s == const.stationary:
        return np.inf, np.inf, np.inf, np.inf, np.inf

    phi = ptmath.angle(rvw[1])
    v = ptmath.norm3d(rvw[1])

    u = get_u(rvw, R, phi, s)

    K = -0.5 * mu * g
    cos_phi = np.cos(phi)
    sin_phi = np.sin(phi)

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
) -> Tuple[float, float, float, float, float]:
    """Get quartic coeffs required to determine the ball-pocket collision time

    (just-in-time compiled)
    """

    if s == const.spinning or s == const.pocketed or s == const.stationary:
        return np.inf, np.inf, np.inf, np.inf, np.inf

    phi = ptmath.angle(rvw[1])
    v = ptmath.norm3d(rvw[1])

    u = get_u(rvw, R, phi, s)

    K = -0.5 * mu * g
    cos_phi = np.cos(phi)
    sin_phi = np.sin(phi)

    ax = K * (u[0] * cos_phi - u[1] * sin_phi)
    ay = K * (u[0] * sin_phi + u[1] * cos_phi)
    bx, by = v * cos_phi, v * sin_phi
    cx, cy = rvw[0, 0], rvw[0, 1]

    A = 0.5 * (ax**2 + ay**2)
    B = ax * bx + ay * by
    C = ax * (cx - a) + ay * (cy - b) + 0.5 * (bx**2 + by**2)
    D = bx * (cx - a) + by * (cy - b)
    E = 0.5 * (a**2 + b**2 + cx**2 + cy**2 - r**2) - (cx * a + cy * b)

    return A, B, C, D, E
