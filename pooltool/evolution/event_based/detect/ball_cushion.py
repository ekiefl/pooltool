from __future__ import annotations

import numpy as np
import quaternion
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
from pooltool.evolution.event_based.detect.ball_position_polynomial import (
    ball_position_polynomial,
)
from pooltool.evolution.event_based.detect.quartic_coefficients import (
    parabola_circle_distance_2d_quartic_coefficients,
)
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.table.components import LinearCushionSegment
from pooltool.physics.utils import get_u_vec
from pooltool.ptmath import quaternion_from_vector_to_vector
from pooltool.ptmath.roots import (
    get_real_positive_smallest_root,
    is_real_number,
    quadratic,
    quartic,
)
from pooltool.system.datatypes import System


@jit(nopython=True, cache=const.use_numba_cache)
def select_ball_linear_cushion_segment_collision_root(
    sorted_real_positive_roots: NDArray[np.float64],
    p_rot_z: NDArray[np.float64],
    start_z: float,
    end_z: float,
):
    """Smallest positive real root that is within the bounds of the cushion segment"""
    for t in sorted_real_positive_roots:
        collision_z = p_rot_z[0] + p_rot_z[1] * t + p_rot_z[2] * t * t
        if start_z < collision_z and collision_z < end_z:
            return t
    return np.inf


def ball_linear_cushion_segment_collison_time(
    ball: Ball, cushion: LinearCushionSegment
):
    """Time until collision between ball and linear cushion segment

    Finds the collision time between the ball's 3D position polynomial and the cushion nose cylinder.

    This works by ignoring the component of ball's 3D position polynomial parallel to the cushion axis,
    reducing the problem to a 2D parabola intersecting with a circle.
    """
    p = ball_position_polynomial(
        ball.state.s,
        ball.state.rvw,
        ball.params.R,
        ball.params.u_r,
        ball.params.u_s,
        ball.params.g,
    )

    unit_z = np.array([0, 0, 1])
    frame_rotation = quaternion_from_vector_to_vector(cushion.unit_axis, unit_z)
    p_rotated = quaternion.rotate_vectors(frame_rotation, p)
    cushion_origin_rotated = quaternion.rotate_vectors(frame_rotation, cushion.p1)

    C = parabola_circle_distance_2d_quartic_coefficients(
        p_rotated.T[0:1],
        cushion_origin_rotated[0:1],
        cushion.nose_radius + ball.params.R,
    )

    # FIXME: quartic solver can't handle cubics or quadratics, so checking for quadratic here
    if np.isclose(C[4], 0.0):
        # C[3] must also be 0.0, and this is a quadratic
        assert np.isclose(C[3], 0.0)
        roots = quadratic.solve(C[2], C[1], C[0])

    roots = quartic.solve(C[4], C[3], C[2], C[1], C[0])

    start_z = cushion_origin_rotated[2]
    end_z = start_z + ptmath.norm3d(cushion.p2 - cushion.p1)
    sorted_real_positive_roots = np.array(
        sorted(root.real for root in roots if is_real_number(root) and root.real > 0)
    )
    return select_ball_linear_cushion_segment_collision_root(
        sorted_real_positive_roots,
        p_rotated.T[2],
        start_z,
        end_z,
    )


@jit(nopython=True, cache=const.use_numba_cache)
def ball_vertical_plane_collision_time(
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
    """Get time until collision between a ball and a vertical plane.

    For ball trajectories limited to the playing surface, this suffices for
    detecting ball collisions with linear cushion segments.

    Note:
        - This is broken for airborne balls.
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
def ball_vertical_cylinder_collision_time(
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
    """Get the time until collision between a ball and a vertical cylinder.

    For ball trajectories limited to the playing surface, this suffices for
    detecting ball collisions with circular cushion segments.

    Note:
        - This is broken for airborne balls.
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

    A = 0.5 * (ax * ax + ay * ay)
    B = ax * bx + ay * by
    C = ax * (cx - a) + ay * (cy - b) + 0.5 * (bx * bx + by * by)
    D = bx * (cx - a) + by * (cy - b)
    E = 0.5 * (a * a + b * b + cx * cx + cy * cy - (r + R) * (r + R)) - (
        cx * a + cy * b
    )

    return get_real_positive_smallest_root(quartic.solve(A, B, C, D, E))


def get_next_ball_linear_cushion_event(
    shot: System, collision_cache: CollisionCache, *, is_3d: bool
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

            if is_3d:
                dtau_E = ball_linear_cushion_segment_collison_time(ball, cushion)
            else:
                dtau_E = ball_vertical_plane_collision_time(
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


def get_next_ball_circular_cushion_event(
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

            if ball.state.s == const.airborne:
                # TODO
                dtau_E = np.inf
            else:
                dtau_E = ball_vertical_cylinder_collision_time(
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
