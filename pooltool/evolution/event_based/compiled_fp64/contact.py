"""Compiled stock 2D Stronge cushion geometry and contact response.

The scalar root solver adapts SciPy 1.18.1's k=1 TOMS748 implementation
in optimize/_zeros_py.py. See the numerical source notices in this package.
"""

import math

import numpy as np
from numba import njit

from pooltool import constants as const
from pooltool.physics.resolve.stronge_compliant import (
    collision_duration,
    compression_duration,
    frequency_n,
    frequency_t,
    phase_angle_restitution,
    t_c_shift,
    u_t_initial_slip,
    v_n_restitution,
    v_t_initial_slip,
    v_t_stick,
)
from pooltool.physics.utils import surface_velocity
from pooltool.ptmath import (
    cross,
    decompose_normal_tangent,
    norm3d,
    point_on_line_closest_to_point,
    unit_vector,
)
from pooltool.ptmath.roots import (
    ABS_OR_REL_CUTOFF,
    ATOL,
    RTOL,
    get_real_smallest_magnitude_root,
    quadratic,
)

CONTACT_OK = 0
CONTACT_GEOMETRY_ERROR = 1
CONTACT_STRONGE_ERROR = 2

_EPS = np.finfo(np.float64).eps
_ROOT_XTOL = 2e-12  # Seconds, the SciPy default.
_ROOT_RTOL = 4 * _EPS
_ROOT_MAXITER = 100


@njit(cache=True, fastmath=False)
def _restitution_residual(
    time,
    initial_stick,
    ratio,
    omega_t,
    omega_n,
    mu,
    normal_speed,
    restitution,
    eta_squared,
    stick_time,
    stick_displacement,
    stick_speed,
):
    normal_phase = phase_angle_restitution(time, omega_n, restitution)
    if initial_stick:
        return abs(-ratio * math.sin(omega_t * time)) - (
            mu * eta_squared * omega_t / omega_n * math.sin(normal_phase)
        )
    tangent_phase = omega_t * (time - stick_time)
    return abs(
        omega_n
        / (mu * normal_speed)
        * (
            stick_displacement * math.cos(tangent_phase)
            - stick_speed / omega_t * math.sin(tangent_phase)
        )
    ) - eta_squared * math.sin(normal_phase)


@njit(cache=True, fastmath=False)
def _rebracket(a, b, fa, fb, point, value):
    if (fa > 0) == (value > 0):
        return point, b, value, fb, a, fa
    return a, point, fa, value, b, fb


@njit(cache=True, fastmath=False)
def _secant(a, b, fa, fb):
    if abs(fb) > abs(fa):
        ratio = fa / fb
        return (-ratio * b + a) / (1 - ratio)
    ratio = fb / fa
    return (-ratio * a + b) / (1 - ratio)


@njit(cache=True, fastmath=False)
def _inverse_cubic_step(a, b, d, e, fa, fb, fd, fe):
    # Neville interpolation of the inverse polynomial at f=0. Keep the
    # reference operation ordering. The historical fourth point starts absent.
    x = (fa, fb, fd, fe)
    y = (a, b, d, e)
    for i in range(4):
        if not math.isfinite(x[i]) or x[i] == 0:
            return math.nan
        for j in range(i):
            if abs(x[i] - x[j]) <= 32 * _EPS:
                return math.nan

    correction = np.empty((4, 4), dtype=np.float64)
    delta = np.empty((4, 4), dtype=np.float64)
    for i in range(4):
        correction[i, 0] = y[i]
        delta[i, 0] = y[i]
    for order in range(1, 4):
        for i in range(order, 4):
            difference = delta[i, order - 1] - correction[i - 1, order - 1]
            denominator = x[i - order] - x[i]
            correction[i, order] = x[i] / denominator * difference
            delta[i, order] = x[i - order] / denominator * difference
    return ((correction[3, 1] + correction[3, 2]) + correction[3, 3]) + e


@njit(cache=True, fastmath=False)
def _quadratic_step(a, b, d, fa, fb, fd):
    slope = (fb - fa) / (b - a)
    second = ((fd - fb) / (d - b) - slope) / (d - a)
    if second == 0:
        return a - fa / slope
    current = a if (second > 0) == (fa > 0) else b
    for _ in range(2):
        derivative = slope + second * (2 * current - a - b)
        if derivative == 0:
            return current if a < current < b else (a + b) / 2.0
        next_value = (
            current
            - ((second * (current - b) + slope) * (current - a) + fa) / derivative
        )
        if not a < next_value < b:
            return current if a < current < b else (a + b) / 2.0
        current = next_value
    return current


@njit(cache=True, fastmath=False)
def _slip_root(a, b, args):
    """Return the bracketed TOMS748 k=1 root or NaN on explicit failure."""
    fa = _restitution_residual(a, *args)
    if fa == 0:
        return a
    fb = _restitution_residual(b, *args)
    if fb == 0:
        return b
    if not (math.isfinite(fa) and math.isfinite(fb)) or (fa > 0) == (fb > 0):
        return math.nan

    c = _secant(a, b, fa, fb)
    if not a < c < b:
        c = (a + b) / 2.0
    fc = _restitution_residual(c, *args)
    if fc == 0:
        return c
    if not math.isfinite(fc):
        return math.nan
    a, b, fa, fb, d, fd = _rebracket(a, b, fa, fb, c, fc)
    e, fe = math.nan, math.nan

    for _ in range(1, _ROOT_MAXITER):
        initial_width = b - a
        c = _inverse_cubic_step(a, b, d, e, fa, fb, fd, fe)
        if not a < c < b:
            c = _quadratic_step(a, b, d, fa, fb, fd)
        if not a < c < b:
            c = (a + b) / 2.0
        fc = _restitution_residual(c, *args)
        if fc == 0:
            return c
        if not math.isfinite(fc):
            return math.nan
        e, fe = d, fd
        a, b, fa, fb, d, fd = _rebracket(a, b, fa, fb, c, fc)

        use_left = abs(fa) < abs(fb)
        near, other = (a, b) if use_left else (b, a)
        f_near, f_other = (fa, fb) if use_left else (fb, fa)
        c = near - 2 * f_near / ((fb - fa) / (b - a))
        if abs(c - near) > 0.5 * (b - a):
            c = (a + b) / 2.0
        elif abs(c - near) <= _EPS * abs(near):
            if math.frexp(f_near)[1] < math.frexp(f_other)[1] - 50:
                c = (31 * near + other) / 32
            else:
                direction = 1 if use_left else -1
                c = near + (direction * abs(c) * _ROOT_RTOL + direction * _ROOT_XTOL)
            if not a < c < b:
                c = (a + b) / 2.0
        fc = _restitution_residual(c, *args)
        if fc == 0:
            return c
        if not math.isfinite(fc):
            return math.nan
        e, fe = d, fd
        a, b, fa, fb, d, fd = _rebracket(a, b, fa, fb, c, fc)

        if b - a > 0.5 * initial_width:
            c = (a + b) / 2.0
            fc = _restitution_residual(c, *args)
            if fc == 0:
                return c
            if not math.isfinite(fc):
                return math.nan
            e, fe = d, fd
            a, b, fa, fb, d, fd = _rebracket(a, b, fa, fb, c, fc)

        if b - a <= _ROOT_XTOL + _ROOT_RTOL * abs(b):
            return (a + b) / 2.0
    return math.nan


@njit(cache=True, fastmath=False)
def _close(value, reference):
    # These are the pinned NumPy defaults in the branch-boundary shortcuts,
    # distinct from SciPy's root tolerance.
    return abs(value - reference) <= 1e-8 + 1e-5 * abs(reference)


@njit(cache=True, fastmath=False)
def _stick_time(ratio, beta, friction, restitution, eta_squared, compression):
    if ratio <= friction * beta:
        cosine = ((ratio / friction) - beta) / (eta_squared - beta)
        if not -1 <= cosine <= 1:
            return math.nan
        phase = (2 / math.pi) * math.acos(cosine)
        if not 0 <= phase <= 1:
            return math.nan
    else:
        cosine = ((ratio / friction) - beta) / (
            eta_squared / restitution - restitution * beta
        )
        if not -1 <= cosine <= 1:
            return math.nan
        phase = (
            (2 / math.pi) * (math.acos(cosine) - t_c_shift(restitution)) * restitution
        )
        if not 1 <= phase <= 1 + restitution:
            return math.nan
    return compression * phase


@njit(cache=True, fastmath=False)
def stronge_velocities(
    tangent_speed, normal_speed, mass, friction, restitution, omega_ratio
):
    """Compute compliant collision velocities, returning NaNs for rejected inputs."""
    if not (
        math.isfinite(tangent_speed)
        and math.isfinite(normal_speed)
        and math.isfinite(mass)
        and math.isfinite(friction)
        and math.isfinite(restitution)
        and math.isfinite(omega_ratio)
        and tangent_speed <= 0
        and normal_speed < 0
        and mass > 0
        and friction > 0
        and restitution > 0
        and 1 < omega_ratio < 2
    ):
        return math.nan, math.nan

    beta = 3.5
    eta_squared = beta / omega_ratio**2
    ratio = tangent_speed / normal_speed
    omega_n = frequency_n(1.0, 1e3, mass)
    omega_t = frequency_t(omega_n, beta, eta_squared)
    if not (math.isfinite(omega_n) and 1 < omega_t / omega_n < 2):
        return math.nan, math.nan
    compression = compression_duration(omega_n)
    finish = collision_duration(compression, restitution)
    initial_boundary = friction * eta_squared
    gross_boundary = friction * ((1 + restitution) * beta - eta_squared / restitution)

    if ratio > gross_boundary:
        final_tangent = tangent_speed - friction * normal_speed * beta * (
            1 + restitution
        )
    elif ratio < initial_boundary:
        if _close(ratio, 0.0):
            slip_time = finish
        elif _close(ratio, initial_boundary):
            slip_time = compression
        else:
            slip_time = _slip_root(
                compression,
                finish,
                (
                    True,
                    ratio,
                    omega_t,
                    omega_n,
                    friction,
                    normal_speed,
                    restitution,
                    eta_squared,
                    0.0,
                    0.0,
                    0.0,
                ),
            )
        if not compression <= slip_time <= finish:
            return math.nan, math.nan
        sticking_speed = v_t_stick(slip_time, omega_t, tangent_speed)
        final_tangent = (
            sticking_speed
            + friction
            * normal_speed
            * beta
            * restitution
            * (1 + math.cos(omega_n * slip_time / restitution + t_c_shift(restitution)))
        )
    else:
        if not initial_boundary <= ratio <= gross_boundary:
            return math.nan, math.nan
        stick_time = _stick_time(
            ratio, beta, friction, restitution, eta_squared, compression
        )
        if not math.isfinite(stick_time):
            return math.nan, math.nan
        displacement = u_t_initial_slip(
            stick_time,
            compression,
            normal_speed,
            friction,
            eta_squared,
            omega_n,
            restitution,
        )
        speed = v_t_initial_slip(
            stick_time,
            compression,
            tangent_speed,
            normal_speed,
            friction,
            beta,
            omega_n,
            restitution,
        )
        if _close(ratio, initial_boundary):
            slip_time = compression
        elif _close(ratio, gross_boundary):
            slip_time = finish
        else:
            slip_time = _slip_root(
                compression,
                finish,
                (
                    False,
                    ratio,
                    omega_t,
                    omega_n,
                    friction,
                    normal_speed,
                    restitution,
                    eta_squared,
                    stick_time,
                    displacement,
                    speed,
                ),
            )
            if not stick_time <= slip_time <= finish:
                return math.nan, math.nan
        sticking_speed = v_t_stick(slip_time, omega_t, speed, displacement, stick_time)
        final_tangent = (
            sticking_speed
            + beta
            * friction
            * normal_speed
            * restitution
            * (1 + math.cos(phase_angle_restitution(slip_time, omega_n, restitution)))
        )

    return final_tangent, v_n_restitution(finish, normal_speed, omega_n, restitution)


@njit(cache=True)
def _nearest_time(alpha, beta, gamma):
    return get_real_smallest_magnitude_root(
        quadratic.solve(alpha, beta, gamma), ABS_OR_REL_CUTOFF, RTOL, ATOL
    )


@njit(cache=True)
def _constrain_to_cloth(pos, p1, p2, axis, radius):
    """Specialize upstream linear-cushion cloth constraint to 2D motion."""
    if pos[2] == radius:
        return pos

    center = point_on_line_closest_to_point(p1, p2, pos)
    arm = pos - center
    length = norm3d(arm)
    direction = arm / length
    horizontal = np.array([axis[1], -axis[0], 0.0])
    vertical_component = (radius - center[2]) / length
    side = 1.0 if np.dot(direction, horizontal) >= 0 else -1.0
    horizontal_component = side * np.sqrt(1.0 - vertical_component**2)
    return center + length * (
        vertical_component * np.array([0.0, 0.0, 1.0])
        + horizontal_component * horizontal
    )


@njit(cache=True)
def _linear_contact(rvw, radius, segment):
    """Position the ball along its trajectory, with the stock normal fallback."""
    p1, p2 = segment[6:9], segment[9:12]
    direction = p2 - p1
    axis = direction / norm3d(direction)
    position, velocity = rvw[0], rvw[1]
    relative = position - p1
    v_perp = velocity - np.dot(velocity, axis) * axis
    r_perp = relative - np.dot(relative, axis) * axis
    target = radius + segment[4] + const.MIN_DIST
    time = _nearest_time(
        np.dot(v_perp, v_perp),
        2 * np.dot(r_perp, v_perp),
        np.dot(r_perp, r_perp) - target**2,
    )
    if not math.isfinite(time) or norm3d(time * velocity) > 5 * const.MIN_DIST:
        center = point_on_line_closest_to_point(p1, p2, position)
        candidate = center + target * unit_vector(position - center)
    else:
        candidate = position + time * velocity

    position = _constrain_to_cloth(candidate, p1, p2, axis, radius)
    relative = position - p1
    normal = unit_vector(relative - np.dot(relative, axis) * axis)
    return position, normal


@njit(cache=True)
def _circular_contact(rvw, radius, segment):
    """Use the stock XY circular kiss and its 3D impulse normal."""
    position, velocity = rvw[0], rvw[1]
    center = np.array([segment[0], segment[1], position[2]])
    diff = position - center
    target = radius + segment[2] + const.MIN_DIST
    time = _nearest_time(
        velocity[0] ** 2 + velocity[1] ** 2,
        2 * (diff[0] * velocity[0] + diff[1] * velocity[1]),
        diff[0] ** 2 + diff[1] ** 2 - target**2,
    )
    if norm3d(time * velocity) > 5 * const.MIN_DIST:
        position = center + target * unit_vector(diff)
    else:
        position = position + time * velocity
    normal = unit_vector(position - np.array([segment[0], segment[1], segment[3]]))
    return position, normal


@njit(cache=True)
def resolve_cushion(rvw, params, segment, is_linear, omega_ratio):
    """Resolve the stock planar Stronge contact on success, or return a failure."""
    radius, mass, restitution, friction = params[0], params[1], params[7], params[8]
    if is_linear:
        position, normal = _linear_contact(rvw, radius, segment)
    else:
        position, normal = _circular_contact(rvw, radius, segment)
    if not np.all(np.isfinite(position)) or not np.all(np.isfinite(normal)):
        return CONTACT_GEOMETRY_ERROR

    candidate = rvw.copy()
    candidate[0] = position
    contact_velocity = surface_velocity(candidate, -normal, radius)
    v_n, v_t, tangent = decompose_normal_tangent(contact_velocity, normal, True)
    v_t_final, v_n_final = stronge_velocities(
        v_t, v_n, mass, friction, restitution, omega_ratio
    )
    if not (math.isfinite(v_t_final) and math.isfinite(v_n_final)):
        return CONTACT_STRONGE_ERROR

    candidate[1] += (v_n_final - v_n) * normal
    tangent_change = ((v_t_final - v_t) / 3.5) * tangent
    candidate[1] += tangent_change
    candidate[2] += (2.5 / radius) * cross(-normal, tangent_change)
    expected = v_n_final * normal + v_t_final * tangent
    actual = surface_velocity(candidate, -normal, radius)
    for i in range(3):
        if not (math.isfinite(actual[i]) and _close(expected[i], actual[i])):
            return CONTACT_STRONGE_ERROR

    candidate[1, 2] = 0.0
    rvw[:, :] = candidate
    return CONTACT_OK
