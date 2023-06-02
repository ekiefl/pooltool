import numpy as np
from numba import jit

import pooltool.constants as c


def wiggle(x, val):
    """Vary a float or int x by +- val according to a uniform distribution"""
    return x + val * (2 * np.random.rand() - 1)


@jit(nopython=True, cache=c.numba_cache)
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


@jit(nopython=True, cache=c.numba_cache)
def quadratic(a, b, c):
    """Solve a quadratic equation At^2 + Bt + C = 0 (just-in-time compiled)"""
    if a == 0:
        u = -c / b
        return u, u
    bp = b / 2
    delta = bp * bp - a * c
    u1 = (-bp - delta**0.5) / a
    u2 = -u1 - b / a
    return u1, u2


def roots(p):
    """Solve multiple polynomial equations

    This is a vectorized implementation of numpy.roots that can solve multiple
    polynomials in a vectorized fashion. The solution is taken from this wonderful
    stackoverflow answer: https://stackoverflow.com/a/35853977

    Parameters
    ==========
    p : array
        A mxn array of polynomial coefficients, where m is the number of equations and
        n-1 is the order of the polynomial. If n is 5 (4th order polynomial), the
        columns are in the order a, b, c, d, e, where these coefficients make up the
        polynomial equation at^4 + bt^3 + ct^2 + dt + e = 0

    Notes
    =====
    - This function is not amenable to numbaization (0.54.1). There are a couple of
      hurdles to address. p[...,None,0] needs to be refactored since None/np.newaxis
      cause compile error. But even bigger an issue is that np.linalg.eigvals is only
      supported for 2D arrays, but the strategy here is to pass np.lingalg.eigvals a
      vectorized 3D array.
    """
    n = p.shape[-1]
    A = np.zeros(p.shape[:1] + (n - 1, n - 1), np.float64)
    A[..., 1:, :-1] = np.eye(n - 2)
    A[..., 0, :] = -p[..., 1:] / p[..., None, 0]
    return np.linalg.eigvals(A)


def min_real_root(p, tol=c.tol):
    """Given an array of polynomial coefficients, find the minimum real root

    Parameters
    ==========
    p : array
        A mxn array of polynomial coefficients, where m is the number of equations and
        n-1 is the order of the polynomial. If n is 5 (4th order polynomial), the
        columns are in the order a, b, c, d, e, where these coefficients make up the
        polynomial equation at^4 + bt^3 + ct^2 + dt + e = 0
    tol : float
        Roots are real if their imaginary components are less than than tol.

    Returns
    =======
    output : (time, index)
        `time` is the minimum real root from the set of polynomials, and `index`
        specifies the index of the responsible polynomial. i.e. the polynomial with the
        root `time` is p[index]
    """
    # Get the roots for the polynomials
    times = roots(p)

    # If the root has a nonzero imaginary component, set to infinity
    # If the root has a nonpositive real component, set to infinity
    times[(abs(times.imag) > tol) | (times.real <= tol)] = np.inf

    # now find the minimum time and the index of the responsible polynomial
    times = np.min(times.real, axis=1)

    return times.min(), times.argmin()


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


@jit(nopython=True, cache=c.numba_cache)
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


@jit(nopython=True, cache=c.numba_cache)
def angle(v2, v1=(1, 0)):
    """Returns counter-clockwise angle of projections of v1 and v2 onto the x-y plane

    (just-in-time compiled)
    """
    ang = np.arctan2(v2[1], v2[0]) - np.arctan2(v1[1], v1[0])

    if ang < 0:
        return 2 * np.pi + ang

    return ang


@jit(nopython=True, cache=c.numba_cache)
def coordinate_rotation_fast(v, phi):
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
