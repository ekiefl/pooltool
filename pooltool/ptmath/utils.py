from collections.abc import Callable
from math import sqrt
from typing import Any

import numpy as np
import quaternion
import scipy.spatial.transform as sp_tf
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const


def solve_transcendental(
    f: Callable[[float], float],
    a: float,
    b: float,
    tol: float = 1e-5,
    max_iter: int = 100,
) -> float:
    """Solve transcendental equation f(x) = 0 in interval [a, b] using bisection method

    Args:
        f:
            A function representing the transcendental equation.
        a:
            The lower bound of the interval.
        b:
            The upper bound of the interval.
        tol:
            The tolerance level for the solution. The function stops when the absolute
            difference between the upper and lower bounds is less than tol.
        max_iter:
            The maximum number of iterations to perform.

    Returns:
        The approximate root of f within the interval [a, b].

    Raises:
        ValueError:
            If f(a) and f(b) have the same sign, indicating no root within the interval.
        RuntimeError:
            If the maximum number of iterations is reached without convergence.
    """
    if f(a) * f(b) >= 0:
        raise ValueError("Function must have opposite signs at the interval endpoints")

    c = (a + b) / 2
    for _ in range(max_iter):
        c = (a + b) / 2
        if f(c) == 0 or (b - a) / 2 < tol:
            return c

        if f(c) * f(a) < 0:
            b = c
        else:
            a = c

    return c


def convert_2D_to_3D(array: NDArray[np.float64]) -> NDArray[np.float64]:
    """Convert a 2D vector to a 3D vector, setting z=0"""
    return np.pad(array, (0, 1), "constant", constant_values=(0,))


def wiggle(x: float, val: float):
    """Vary a float or int x by +- val according to a uniform distribution"""
    return x + val * (2 * np.random.rand() - 1)


def are_points_on_same_side(p1, p2, p3, p4) -> bool:
    """Are points p3, p4 are on the same side of the line formed by points p1 and p2?

    Accepts indexable objects. This is a 2D function, but if higher dimensions are
    provided, that's ok (only the first two dimensions will be used).
    """

    def cross_product_sign(a, b, c):
        """Calculate the sign of the cross product of vectors (a, b) and (a, c)"""
        return (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])

    cp1 = cross_product_sign(p1, p2, p3)
    cp2 = cross_product_sign(p1, p2, p4)

    # If both cross products have the same sign, then p3 and p4 are on the same side
    return cp1 * cp2 >= 0


def find_intersection_2D(
    l1x: float,
    l1y: float,
    l10: float,
    l2x: float,
    l2y: float,
    l20: float,
) -> tuple[float, float]:
    """Find the intersection point of two lines in 2D space

    The lines are defined by their linear equations in the general form:
    (l1x)x + (l1y)y + l10 = 0 and (l2x)x + (l2y)y + l20 = 0.

    Args:
        l1x: The coefficient of x in the first line equation.
        l1y: The coefficient of y in the first line equation.
        l10: The constant term in the first line equation.
        l2x: The coefficient of x in the second line equation.
        l2y: The coefficient of y in the second line equation.
        l20: The constant term in the second line equation.

    Returns:
        A tuple (x, y) representing the intersection point if the lines intersect at a
        single point. Returns None if the lines are parallel or coincident (no unique
        intersection).
    """
    if (determinant := l1x * l2y - l2x * l1y) == 0:
        raise ValueError("Lines are parallel or coincident, no unique intersection")

    x = (l1y * l20 - l2y * l10) / determinant
    y = (l2x * l10 - l1x * l20) / determinant

    return x, y


@jit(nopython=True, cache=const.use_numba_cache)
def cross(u: NDArray[np.float64], v: NDArray[np.float64]) -> NDArray[np.float64]:
    """Compute cross product u x v, where u and v are 3-dimensional vectors

    (just-in-time compiled)
    """
    return np.array(
        [
            u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0],
        ]
    )


def unit_vector_slow(
    vector: NDArray[np.float64], handle_zero: bool = False
) -> NDArray[np.float64]:
    """Returns the unit vector of the vector.

    "Slow", but supports more than just 3D.

    Args:
        handle_zero:
            If True and vector = <0,0,0>, <0,0,0> is returned.
    """
    if len(vector.shape) > 1:
        norm = np.linalg.norm(vector, axis=1, keepdims=True)
        if handle_zero:
            norm[(norm == 0).all(axis=1), :] = 1
        return vector / norm
    else:
        norm = np.linalg.norm(vector)
        if norm == 0 and handle_zero:
            norm = 1
        return vector / norm


@jit(nopython=True, cache=const.use_numba_cache)
def unit_vector(
    vector: NDArray[np.float64], handle_zero: bool = False
) -> NDArray[np.float64]:
    """Returns the unit vector of the vector (just-in-time compiled)

    Args:
        handle_zero:
            If True and vector = <0,0,0>, <0,0,0> is returned.

    Notes:
        - Only supports 3D (for 2D see unit_vector_slow)
    """
    norm = norm3d(vector)
    if handle_zero and norm == 0.0:
        norm = 1.0
    return vector / norm


@jit(nopython=True, cache=const.use_numba_cache)
def angle(v2: NDArray[np.float64], v1: NDArray[np.float64] = np.array([1, 0])) -> float:
    """Returns counter-clockwise angle of projections of v1 and v2 onto the x-y plane

    (just-in-time compiled)
    """
    ang = np.arctan2(v2[1], v2[0]) - np.arctan2(v1[1], v1[0])

    if ang < 0:
        return 2 * np.pi + ang

    return ang


def angle_between_vectors(a: NDArray[np.float64], b: NDArray[np.float64]) -> float:
    """Compute the angle between two 3D vectors in radians.

    Returns:
        The angle between vectors a and b in radians. Can take on values within [0, pi].
    """
    return np.acos(np.dot(a, b) / (norm3d(a) * norm3d(b)))


def rotation_from_vector_to_vector(
    a: NDArray[np.float64], b: NDArray[np.float64]
) -> sp_tf.Rotation:
    """Compute the rotation that transforms vector a to vector b.

    Returns:
        A scipy Rotation object representing the rotation from a to b.
    """
    angle = angle_between_vectors(a, b)
    axis = unit_vector(cross(a, b))
    return sp_tf.Rotation.from_rotvec(axis * angle)


def quaternion_from_vector_to_vector(
    a: NDArray[np.float64], b: NDArray[np.float64]
) -> Any:
    """Compute the quaternion representing the rotation from vector a to vector b

    Args:
        a: Initial 3D vector
        b: Target 3D vector

    Returns:
        A quaternion representing the rotation from a to b.
    """
    angle = angle_between_vectors(a, b)
    axis = unit_vector(cross(a, b), True)
    return quaternion.from_rotation_vector(axis * angle)


@jit(nopython=True, cache=const.use_numba_cache)
def coordinate_rotation(v: NDArray[np.float64], phi: float) -> NDArray[np.float64]:
    """Rotate vector/matrix from one frame of reference to another (3D FIXME)

    (just-in-time compiled)
    """
    cos_phi = np.cos(phi)
    sin_phi = np.sin(phi)
    rotation = np.zeros((3, 3), np.float64)
    rotation[0, 0] = cos_phi
    rotation[0, 1] = -sin_phi
    rotation[1, 0] = sin_phi
    rotation[1, 1] = cos_phi
    rotation[2, 2] = 1

    return np.dot(rotation, v)


@jit(nopython=True, cache=const.use_numba_cache)
def point_on_line_closest_to_point(
    p1: NDArray[np.float64], p2: NDArray[np.float64], p0: NDArray[np.float64]
) -> NDArray[np.float64]:
    """Returns point on line defined by points p1 and p2 closest to the point p0

    Equations from https://mathworld.wolfram.com/Point-LineDistance3-Dimensional.html
    """
    diff = p2 - p1
    t = -np.dot(p1 - p0, diff) / np.dot(diff, diff)
    return p1 + diff * t


@jit(nopython=True, cache=const.use_numba_cache)
def squared_norm3d(vec: NDArray[np.float64]) -> float:
    """Calculate the squared norm of a 3D vector"""
    return vec[0] ** 2 + vec[1] ** 2 + vec[2] ** 2


@jit(nopython=True, cache=const.use_numba_cache)
def norm3d(vec: NDArray[np.float64]) -> float:
    """Calculate the norm of a 3D vector

    This is ~10x faster than np.linalg.norm

    >>> import numpy as np
    >>> from pooltool.ptmath import *
    >>> vec = np.random.rand(3)
    >>> norm3d(vec)
    >>> %timeit np.linalg.norm(vec)
    >>> %timeit norm3d(vec)
    2.65 µs ± 63 ns per loop (mean ± std. dev. of 7 runs, 100,000 loops each)
    241 ns ± 2.57 ns per loop (mean ± std. dev. of 7 runs, 1,000,000 loops each)
    """
    return sqrt(squared_norm3d(vec))


@jit(nopython=True, cache=const.use_numba_cache)
def squared_norm2d(vec: NDArray[np.float64]) -> float:
    """Calculate the squared norm of a 2D vector"""
    return vec[0] ** 2 + vec[1] ** 2


@jit(nopython=True, cache=const.use_numba_cache)
def norm2d(vec: NDArray[np.float64]) -> float:
    """Calculate the norm of a 2D vector

    This is faster than np.linalg.norm
    """
    return sqrt(squared_norm2d(vec))


@jit(nopython=True, cache=const.use_numba_cache)
def surface_velocity(
    rvw: NDArray[np.float64], d: NDArray[np.float64], R: float
) -> NDArray[np.float64]:
    """Compute velocity of a point on ball's surface (specified by unit direction vector)"""
    _, v, w = rvw
    return v + cross(w, R * d)


@jit(nopython=True, cache=const.use_numba_cache)
def tangent_surface_velocity(
    rvw: NDArray[np.float64], d: NDArray[np.float64], R: float
) -> NDArray[np.float64]:
    """Compute velocity tangent to surface at a point on ball's surface (specified by unit direction vector)"""
    _, v, w = rvw
    v_t = v - np.sum(v * d) * d
    return v_t + cross(w, R * d)


@jit(nopython=True, cache=const.use_numba_cache)
def rel_velocity(rvw: NDArray[np.float64], R: float) -> NDArray[np.float64]:
    """Compute velocity of ball's point of contact with the cloth relative to the cloth

    This vector is non-zero whenever the ball is sliding
    """
    return surface_velocity(rvw, np.array([0.0, 0.0, -1.0], dtype=np.float64), R)


@jit(nopython=True, cache=const.use_numba_cache)
def get_u_vec(
    rvw: NDArray[np.float64], phi: float, R: float, s: int
) -> NDArray[np.float64]:
    if s == const.rolling:
        return np.array([1.0, 0.0, 0.0])

    rel_vel = rel_velocity(rvw, R)

    if (rel_vel == 0.0).all():
        return np.array([1.0, 0.0, 0.0])

    return coordinate_rotation(unit_vector(rel_vel), -phi)


@jit(nopython=True, cache=const.use_numba_cache)
def get_slide_time(rvw: NDArray[np.float64], R: float, u_s: float, g: float) -> float:
    if u_s == 0.0:
        return np.inf

    return 2 * norm3d(rel_velocity(rvw, R)) / (7 * u_s * g)


@jit(nopython=True, cache=const.use_numba_cache)
def get_roll_time(rvw: NDArray[np.float64], u_r: float, g: float) -> float:
    if u_r == 0.0:
        return np.inf

    _, v, _ = rvw
    return norm3d(v) / (u_r * g)


@jit(nopython=True, cache=const.use_numba_cache)
def get_spin_time(rvw: NDArray[np.float64], R: float, u_sp: float, g: float) -> float:
    if u_sp == 0.0:
        return np.inf

    _, _, w = rvw
    return np.abs(w[2]) * 2 / 5 * R / u_sp / g


def get_ball_energy(rvw: NDArray[np.float64], R: float, m: float) -> float:
    """Get the energy of a ball

    Currently calculating linear and rotational kinetic energy. Need to add potential
    energy if z-axis is freed
    """
    # Linear
    LKE = m * norm3d(rvw[1]) ** 2 / 2

    # Rotational
    RKE = (2 / 5 * m * R**2) * norm3d(rvw[2]) ** 2 / 2

    return LKE + RKE


def is_overlapping(
    rvw1: NDArray[np.float64], rvw2: NDArray[np.float64], R1: float, R2: float
) -> bool:
    return norm3d(rvw1[0] - rvw2[0]) < (R1 + R2)


@jit(nopython=True, cache=const.use_numba_cache)
def tip_contact_offset(
    cue_center_offset: NDArray[np.float64], tip_radius: float, ball_radius: float
) -> NDArray[np.float64]:
    """Calculate the ball contact point offset from the cue tip center offset.

    This function converts the offset of the cue tip's center (relative to the ball's center,
    and normalized by the ball's radius) into the offset of the contact point on the ball's surface.

    The conversion is based on the geometry of two circles in contact. Since the distance from the
    ball's center to the cue tip's center is (ball_radius + tip_radius) while the ball's surface is
    at a distance ball_radius, the contact point lies along the same line scaled by the factor

        1 / (1 + tip_radius/ball_radius).

    In other words, if (a, b) represent the cue tip center offset, then the ball is struck at

        (a, b) / (1 + tip_radius/ball_radius).

    Args:
        cue_center_offset:
            A 2D vector (e.g., [a, b]) representing the offset of the cue tip center
            relative to the ball center (normalized by the ball's radius).
        tip_radius: The radius of the cue tip.
        ball_radius: The radius of the ball.

    Returns:
        NDArray[np.float64]:
            A 2D vector representing the offset of the contact point on the ball's
            surface, normalized by the ball's radius.
    """
    return cue_center_offset / (1 + tip_radius / ball_radius)


@jit(nopython=True, cache=const.use_numba_cache)
def tip_center_offset(
    tip_center_offset: NDArray[np.float64], tip_radius: float, ball_radius: float
) -> NDArray[np.float64]:
    """Calculate the cue tip center offset from a given contact point offset on the ball.

    This function performs the inverse transformation of `tip_contact_offset`. Given a 2D contact point
    offset on the ball’s surface (normalized by the ball's radius), it computes the corresponding cue tip
    center offset. Since the cue tip’s center is located an extra tip_radius beyond the ball’s surface,
    the transformation scales the contact offset by

        1 + tip_radius/ball_radius.

    Args:
        cue_center_offset:
            A 2D vector (e.g., [a, b]) representing the offset of the cue tip center
            relative to the ball center (normalized by the ball's radius).
        tip_radius: The radius of the cue tip.
        ball_radius: The radius of the ball.

    Returns:
        NDArray[np.float64]: A 2D vector representing the offset of the cue tip's center relative to the
            ball's center (normalized by the ball's radius).
    """
    return tip_center_offset * (1 + tip_radius / ball_radius)
