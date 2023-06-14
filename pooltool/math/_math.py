import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const


def wiggle(x, val):
    """Vary a float or int x by +- val according to a uniform distribution"""
    return x + val * (2 * np.random.rand() - 1)


@jit(nopython=True, cache=const.numba_cache)
def cross(u, v):
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


def unit_vector_slow(vector, handle_zero=False):
    """Returns the unit vector of the vector.

    Parameters
    ==========
    handle_zero: bool, False
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


@jit(nopython=True, cache=const.numba_cache)
def unit_vector(vector, handle_zero=False):
    """Returns the unit vector of the vector (just-in-time compiled)

    Parameters
    ==========
    handle_zero: bool, False
        If True and vector = <0,0,0>, <0,0,0> is returned.

    Notes
    =====
    - Only supports 3D (for 2D see unit_vector_slow)
    """
    norm = np.sqrt(vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2)
    if handle_zero and norm == 0.0:
        norm = 1.0
    return vector / norm


@jit(nopython=True, cache=const.numba_cache)
def angle(v2, v1=(1, 0)):
    """Returns counter-clockwise angle of projections of v1 and v2 onto the x-y plane

    (just-in-time compiled)
    """
    ang = np.arctan2(v2[1], v2[0]) - np.arctan2(v1[1], v1[0])

    if ang < 0:
        return 2 * np.pi + ang

    return ang


@jit(nopython=True, cache=const.numba_cache)
def coordinate_rotation(v, phi):
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


@jit(nopython=True, cache=const.numba_cache)
def point_on_line_closest_to_point(p1, p2, p0):
    """Returns point on line defined by points p1 and p2 closest to the point p0

    Equations from https://mathworld.wolfram.com/Point-LineDistance3-Dimensional.html
    """
    diff = p2 - p1
    t = -np.dot(p1 - p0, diff) / np.dot(diff, diff)
    return p1 + diff * t
