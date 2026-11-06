"""Numeric forms of the stock 2D ball, cue, and transition resolvers."""

import math
from collections.abc import Callable
from typing import Any, cast

import numpy as np
from numba import njit

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.physics.resolve.ball_ball.core import (
    _fallback_positions,
    _velocity_positions,
)
from pooltool.physics.resolve.ball_ball.frictional_inelastic import (
    _resolve_ball_ball_x_normal,
)
from pooltool.physics.resolve.stick_ball.instantaneous_point import cue_strike
from pooltool.physics.resolve.stick_ball.squirt import get_squirt_angle
from pooltool.physics.utils import final_ball_motion_state as final_motion
from pooltool.physics.utils import tangent_surface_velocity

# Numba's dynamic decorator changes the callable into a dispatcher. Its type
# information does not describe the decorator-factory overload.
_velocity_positions_jit = cast(
    Callable[..., Any], njit(cache=const.use_numba_cache)(_velocity_positions)
)
_fallback_positions_jit = cast(
    Callable[..., Any], njit(cache=const.use_numba_cache)(_fallback_positions)
)
_cue_strike = cast(Callable[..., Any], njit(cache=const.use_numba_cache)(cue_strike))
_squirt = cast(Callable[..., Any], njit(cache=const.use_numba_cache)(get_squirt_angle))


@njit(cache=const.use_numba_cache)
def _make_kiss(left, right, s_left, s_right, radius):
    r1, r2 = left[0], right[0]
    spacer = const.MIN_DIST
    target = radius + radius + spacer
    use_velocity, p1, p2 = False, r1, r2
    if s_left not in (
        const.stationary,
        const.spinning,
        const.pocketed,
    ) or s_right not in (
        const.stationary,
        const.spinning,
        const.pocketed,
    ):
        use_velocity, p1, p2 = _velocity_positions_jit(
            r1, r2, left[1], right[1], target, spacer
        )
    if not use_velocity:
        if ptmath.norm3d(r2 - r1) == 0:
            return False
        p1, p2 = _fallback_positions_jit(r1, r2, target)
    # Equal-radius planar inputs keep both centers on the table in either path.
    left[0], right[0] = p1, p2
    return True


@njit(cache=const.use_numba_cache)
def _separate_continually_touching(left, right):
    v1, v2 = left[1], right[1]
    s1, s2 = ptmath.norm3d(v1), ptmath.norm3d(v2)
    if s1 <= 0 or s2 <= 0:
        return True
    axis = ptmath.unit_vector(right[0] - left[0])
    p1, p2 = np.dot(v1, axis), np.dot(v2, axis)
    if abs(p2 - p1) < 0.01 and np.dot(v1, v2) / (s1 * s2) > 0.9:
        stolen = 0.10 * (p1 if p1 > p2 else -p2)
        n1 = v1 - p1 * axis + (p1 - stolen) * axis
        n2 = v2 - p2 * axis + (p2 + stolen) * axis
        if not np.allclose(v1 + v2, n1 + n2, rtol=1e-10):
            return False
        left[1], right[1] = n1, n2
    return True


@njit(cache=const.use_numba_cache)
def _ball_ball(left, right, radius, friction, restitution):
    frame = ptmath.rotation_matrix_from_vector_to_vector(
        right[0] - left[0], np.array([1.0, 0.0, 0.0])
    )
    incoming_left = ptmath.rotate_vectors(frame, left[1:3])
    incoming_right = ptmath.rotate_vectors(frame, right[1:3])
    v1, w1, v2, w2 = _resolve_ball_ball_x_normal(
        incoming_left[0],
        incoming_left[1],
        incoming_right[0],
        incoming_right[1],
        radius,
        friction,
        restitution,
    )
    outgoing = np.empty((2, 3))
    outgoing[0], outgoing[1] = v1, w1
    left[1:3] = ptmath.rotate_vectors(frame.T, outgoing)
    outgoing[0], outgoing[1] = v2, w2
    right[1:3] = ptmath.rotate_vectors(frame.T, outgoing)


@njit(cache=const.use_numba_cache)
def resolve_ball_pair(
    left, right, s_left, s_right, left_params, right_params, friction
):
    radius = left_params[0]
    if not _make_kiss(left, right, s_left, s_right, radius):
        return False, s_left, s_right
    normal = ptmath.unit_vector(right[0] - left[0])
    v1 = tangent_surface_velocity(left, normal, radius)
    v2 = tangent_surface_velocity(right, -normal, right_params[0])
    u = friction[0] + friction[1] * math.exp(-friction[2] * ptmath.norm3d(v1 - v2))
    restitution = (left_params[6] + right_params[6]) / 2
    _ball_ball(left, right, radius, u, restitution)
    left[1, 2] = right[1, 2] = 0.0
    after_left = final_motion(left, radius)
    after_right = final_motion(right, right_params[0])
    return _separate_continually_touching(left, right), after_left, after_right


@njit(cache=const.use_numba_cache)
def resolve_cue(rvw, params, strike, specs):
    speed, heading, theta, a, b = strike
    mass, end_mass, english, squirt = specs
    radius, ball_mass = params[0], params[1]
    theta_rad = theta * np.pi / 180
    c = np.sqrt(1.0 - a**2 - b**2)
    contact = np.array(
        [
            a,
            np.cos(theta_rad) * c - np.sin(theta_rad) * b,
            np.sin(theta_rad) * c + np.cos(theta_rad) * b,
        ]
    )
    v, w = _cue_strike(ball_mass, mass, radius, speed, heading, theta, radius * contact)
    rvw[1] = ptmath.coordinate_rotation(v, _squirt(ball_mass, end_mass, a, squirt))
    rvw[1, 2] = 0.0
    rvw[2] = w * english


@njit(cache=const.use_numba_cache)
def resolve_transition(rvw, start, end):
    if start == const.sliding and end == const.rolling:
        return True
    if start not in (const.rolling, const.spinning):
        return False
    if end == const.spinning and start == const.rolling:
        if not np.all(np.abs(rvw[1]) < 1e-12) or not np.all(np.abs(rvw[2, :2]) < 1e-12):
            return False
        rvw[1, :] = 0
        rvw[2, :2] = 0
        return True
    if end == const.stationary:
        if not np.all(np.abs(rvw[1:]) < 1e-12):
            return False
        rvw[1:, :] = 0
        return True
    return False
