#! /usr/bin/env python

import importlib.util
import linecache
import os
import pickle
import tracemalloc

import numpy as np
import pprofile
from numba import jit
from panda3d.core import Filename

import pooltool.constants as c


class classproperty(property):
    """Decorator for a class property

    Examples:
        >>> from pooltool.utils import classproperty
        >>> class Test:
        >>>     @classproperty
        >>>     def foo(cls):
        >>>         return cls.__name__
    """

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


def save_pickle(x, path):
    """Save an object `x` to filepath `path`"""
    with open(path, "wb") as f:
        pickle.dump(x, f)


def load_pickle(path):
    with open(path, "rb") as f:
        return pickle.load(f)


def is_pickleable(obj):
    """https://stackoverflow.com/a/53398070"""
    try:
        pickle.dumps(obj)
    except pickle.PicklingError:
        return False
    except TypeError:
        return False
    return True


def panda_path(path) -> str:
    panda_path = Filename.fromOsSpecific(str(path))
    panda_path.makeTrueCase()
    return str(panda_path)


def get_total_memory_usage(keep_raw=False):
    """Get the total memory, including children

    Parameters
    ==========
    keep_raw : bool, False
        A human readable format is returned, e.g. "1.41 GB". If keep_raw, the raw number
        is returned, e.g. 1515601920
    """
    if importlib.util.find_spec("psutil") is None:
        # psutil does not exist in this distribution
        return "??"
    else:
        import psutil

    current_process = psutil.Process(os.getpid())
    mem = current_process.memory_info().rss
    for child in current_process.children(recursive=True):
        try:
            mem += child.memory_info().rss
        except Exception:
            pass

    return mem if keep_raw else human_readable_file_size(mem)


def display_top_memory_usage(snapshot, key_type="lineno", limit=10):
    """A pretty-print for the tracemalloc memory usage module

    Modified from https://docs.python.org/3/library/tracemalloc.html

    Examples
    ========
    >>> import tracemalloc
    >>> import pooltool.utils as utils
    >>> tracemalloc.start()
    >>> snap = tracemalloc.take_snapshot
    >>> utils.display_top_memory_usage(snap)
    Top 10 lines
    #1: anvio/bamops.py:160: 4671.3 KiB
        constants.cigar_consumption,
    #2: anvio/bamops.py:96: 2571.6 KiB
        self.cigartuples = np.array(read.cigartuples)
    #3: python3.6/linecache.py:137: 1100.0 KiB
        lines = fp.readlines()
    #4: <frozen importlib._bootstrap_external>:487: 961.4 KiB
    #5: typing/templates.py:627: 334.3 KiB
        return type(base)(name, (base,), dct)
    #6: typing/templates.py:923: 315.7 KiB
        class Template(cls):
    #7: python3.6/_weakrefset.py:84: 225.2 KiB
        self.data.add(ref(item, self._remove))
    #8: targets/npyimpl.py:411: 143.2 KiB
        class _KernelImpl(_Kernel):
    #9: _vendor/pyparsing.py:3349: 139.7 KiB
        self.errmsg = "Expected " + _ustr(self)
    #10: typing/context.py:456: 105.1 KiB
        def on_disposal(wr, pop=self._globals.pop):
    3212 other: 4611.9 KiB
    Total allocated size: 15179.4 KiB
    """

    snapshot = snapshot.filter_traces(
        (
            tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
            tracemalloc.Filter(False, "<unknown>"),
        )
    )
    top_stats = snapshot.statistics(key_type)

    print("Top %s lines" % limit)
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        # replace "/path/to/module/file.py" with "module/file.py"
        filename = os.sep.join(frame.filename.split(os.sep)[-2:])
        print(
            "#%s: %s:%s: %.1f KiB" % (index, filename, frame.lineno, stat.size / 1024)
        )
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print("    %s" % line)

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print("%s other: %.1f KiB" % (len(other), size / 1024))
    total = sum(stat.size for stat in top_stats)
    print("Total allocated size: %.1f KiB" % (total / 1024))


def human_readable_file_size(nbytes):
    suffixes = ["B", "KB", "MB", "GB", "TB", "PB"]
    if nbytes == 0:
        return "0 B"
    i = 0
    while nbytes >= 1024 and i < len(suffixes) - 1:
        nbytes /= 1024.0
        i += 1
    f = ("%.2f" % nbytes).rstrip("0").rstrip(".")
    return "%s %s" % (f, suffixes[i])


def wiggle(x, val):
    """Vary a float or int x by +- val according to a uniform distribution"""
    return x + val * (2 * np.random.rand() - 1)


def cross(u, v):
    """Compute cross product u x v, where u and v are 3-dimensional vectors"""
    return np.array(
        [
            u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0],
        ]
    )


@jit(nopython=True, cache=c.numba_cache)
def cross_fast(u, v):
    """Compute cross product u x v, where u and v are 3-dimensional vectors

    (just-in-time compiled)

    Notes
    =====
    - Speed comparison in pooltool/tests/speed/cross.py
    """
    return np.array(
        [
            u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0],
        ]
    )


def get_rel_velocity(rvw, R):
    _, v, w = rvw
    return v + R * cross(np.array([0, 0, 1]), w)


@jit(nopython=True, cache=c.numba_cache)
def get_rel_velocity_fast(rvw, R):
    """
    Notes
    =====
    - Speed comparison in pooltool/tests/speed/get_rel_velocity.py
    """
    _, v, w = rvw
    return v + R * cross_fast(np.array([0.0, 0.0, 1.0], dtype=np.float64), w)


def quadratic(a, b, c):
    """Solve a quadratic equation At^2 + Bt + C = 0"""
    if a == 0:
        u = -c / b
        return u, u
    bp = b / 2
    delta = bp * bp - a * c
    u1 = (-bp - delta**0.5) / a
    u2 = -u1 - b / a
    return u1, u2


@jit(nopython=True, cache=c.numba_cache)
def quadratic_fast(a, b, c):
    """Solve a quadratic equation At^2 + Bt + C = 0 (just-in-time compiled)

    Notes
    =====
    - Speed comparison in pooltool/tests/speed/quadratic.py
    """
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


@jit(nopython=True, cache=c.numba_cache)
def roots_fast(p):
    """Solve multiple polynomial equations (just-in-time compiled)

    Notes
    =====
    - Speed comparison in pooltool/tests/speed/roots.py
    """
    M, N = p.shape
    p = p.astype(np.complex128)
    roots = np.zeros((M, N - 1), np.complex128)
    for m in range(M):
        roots[m, :] = np.roots(p[m, :])
    return roots


def min_real_root(p, tol=1e-12):
    """Given an array of polynomial coefficients, find the minimum real root

    Parameters
    ==========
    p : array
        A mxn array of polynomial coefficients, where m is the number of equations and
        n-1 is the order of the polynomial. If n is 5 (4th order polynomial), the
        columns are in the order a, b, c, d, e, where these coefficients make up the
        polynomial equation at^4 + bt^3 + ct^2 + dt + e = 0
    tol : float, 1e-12
        Roots are considered if they have

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


@jit(nopython=True, cache=c.numba_cache)
def min_real_root_fast(p, tol=1e-12):
    """Given an array of polynomial coefficients, find the minimum real root

    (just-in-time compiled)

    Notes
    =====
    - Speed comparison in pooltool/tests/speed/min_real_root.py
    """
    # Get the roots for the polynomials
    times = roots_fast(p)
    M, N = times.shape

    min_root, min_index = np.inf, 0
    for m in range(M):
        for n in range(N):
            el = times[m, n]
            if np.abs(el.imag) > tol:
                continue
            elif el.real < tol:
                continue

            if el.real < min_root:
                min_root = el.real
                min_index = m

    return min_root, min_index


def unit_vector(vector, handle_zero=False):
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
def unit_vector_fast(vector, handle_zero=False):
    """Returns the unit vector of the vector (just-in-time compiled)

    Notes
    =====
    - Unlike unit_vector, this does not support 2D arrays
    - Speed comparison in pooltool/tests/speed/unit_vector.py
    """
    norm = np.sqrt(vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2)
    if handle_zero and norm == 0.0:
        norm = 1.0
    return vector / norm


def angle(v2, v1=(1, 0)):
    """Returns counter-clockwise angle of projections of v1 and v2 onto the x-y plane"""
    ang = np.arctan2(v2[1], v2[0]) - np.arctan2(v1[1], v1[0])

    if ang < 0:
        return 2 * np.pi + ang

    return ang


@jit(nopython=True, cache=c.numba_cache)
def orientation(p, q, r):
    """Find the orientation of an ordered triplet (p, q, r)

    See https://www.geeksforgeeks.org/orientation-3-ordered-points/amp/

    Notes
    =====
    - 3D points may be passed but only the x and y components are used

    Returns
    =======
    output : int
        0 : Collinear points, 1 : Clockwise points, 2 : Counterclockwise
    """
    val = ((q[1] - p[1]) * (r[0] - q[0])) - ((q[0] - p[0]) * (r[1] - q[1]))
    if val > 0:
        # Clockwise orientation
        return 1
    elif val < 0:
        # Counterclockwise orientation
        return 2
    else:
        # Collinear orientation
        return 0


@jit(nopython=True, cache=c.numba_cache)
def angle_fast(v2, v1=(1, 0)):
    """Returns counter-clockwise angle of projections of v1 and v2 onto the x-y plane

    (just-in-time compiled)

    Notes
    =====
    - Speed comparison in pooltool/tests/speed/angle.py
    """
    ang = np.arctan2(v2[1], v2[0]) - np.arctan2(v1[1], v1[0])

    if ang < 0:
        return 2 * np.pi + ang

    return ang


def coordinate_rotation(v, phi):
    """Rotate vector/matrix from one frame of reference to another (3D FIXME)"""
    cos_phi = np.cos(phi)
    sin_phi = np.sin(phi)
    rotation = np.array([[cos_phi, -sin_phi, 0], [sin_phi, cos_phi, 0], [0, 0, 1]])

    return np.dot(rotation, v)


@jit(nopython=True, cache=c.numba_cache)
def coordinate_rotation_fast(v, phi):
    """Rotate vector/matrix from one frame of reference to another (3D FIXME)

    (just-in-time compiled)

    Notes
    =====
    - Speed comparison in pooltool/tests/speed/coordinate_rotation.py
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


class PProfile(pprofile.Profile):
    """Small wrapper for pprofile that accepts a filepath and outputs cachegrind file"""

    def __init__(self, path, run=True):
        self.run = run
        self.path = path
        pprofile.Profile.__init__(self)

    def __enter__(self):
        if self.run:
            return pprofile.Profile.__enter__(self)
        else:
            return self

    def __exit__(self, *args):
        if self.run:
            pprofile.Profile.__exit__(self, *args)
            self.dump_stats(self.path)
