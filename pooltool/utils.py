#! /usr/bin/env python

import os
import numpy as np
import cmath
import pickle
import tempfile
import linecache
import tracemalloc
import importlib.util

from numba import jit
from panda3d.core import Filename

def save_pickle(x, path):
    """Save an object `x` to filepath `path`"""
    with open(path, 'wb') as f:
        pickle.dump(x, f)


def load_pickle(path):
    with open(path, 'rb') as f:
        return pickle.load(f)


def panda_path(path):
    return str(Filename.fromOsSpecific(str(path)))


def get_temp_file_path():
    f = tempfile.NamedTemporaryFile(delete=False)
    temp_file_name = f.name
    f.close()
    return temp_file_name


def get_total_memory_usage(keep_raw=False):
    """Get the total memory, including children

    Parameters
    ==========
    keep_raw : bool, False
        A human readable format is returned, e.g. "1.41 GB". If keep_raw, the raw number is
        returned, e.g. 1515601920
    """
    if importlib.util.find_spec('psutil') is None:
        # psutil does not exist in this distribution
        return '??'
    else:
        import psutil

    current_process = psutil.Process(os.getpid())
    mem = current_process.memory_info().rss
    for child in current_process.children(recursive=True):
        try:
            mem += child.memory_info().rss
        except:
            pass

    return mem if keep_raw else human_readable_file_size(mem)


def display_top_memory_usage(snapshot, key_type='lineno', limit=10):
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

    snapshot = snapshot.filter_traces((
        tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
        tracemalloc.Filter(False, "<unknown>"),
    ))
    top_stats = snapshot.statistics(key_type)

    print("Top %s lines" % limit)
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        # replace "/path/to/module/file.py" with "module/file.py"
        filename = os.sep.join(frame.filename.split(os.sep)[-2:])
        print("#%s: %s:%s: %.1f KiB"
              % (index, filename, frame.lineno, stat.size / 1024))
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print('    %s' % line)

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print("%s other: %.1f KiB" % (len(other), size / 1024))
    total = sum(stat.size for stat in top_stats)
    print("Total allocated size: %.1f KiB" % (total / 1024))


def human_readable_file_size(nbytes):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    if nbytes == 0: return '0 B'
    i = 0
    while nbytes >= 1024 and i < len(suffixes)-1:
        nbytes /= 1024.
        i += 1
    f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
    return '%s %s' % (f, suffixes[i])


def wiggle(x, val):
    """Vary a float or int x by +- val according to a uniform distribution"""
    return x + val*(2*np.random.rand() - 1)


def cross(v, u):
    """Compute cross product v x u, where v and u are 3-dimensional vectors"""
    return np.array([
        v[1]*u[2] - v[2]*u[1],
        v[2]*u[0] - v[0]*u[2],
        v[0]*u[1] - v[1]*u[0],
    ])


@jit(nopython=True, cache=True)
def quadratic(a,b,c):
    """Solve a quadratic equation At^2 + Bt + C = 0"""
    if a == 0:
        u = -c/b
        return u, u
    bp=b/2
    delta=bp*bp-a*c
    u1=(-bp-delta**.5)/a
    u2=-u1-b/a
    return u1,u2


def roots(p):
    """Simultaneously solve polynomial equations

    This is a vectorized implementation of numpy.roots that can solve multiple polynomials in a
    vectorized fashion. The solution is taken from this wonderful stackoverflow answer:
    https://stackoverflow.com/a/35853977

    Parameters
    ==========
    p : array
        A mxn array of polynomial coefficients, where m is the number of equations and n-1 is the
        order of the polynomial. If n is 5 (4th order polynomial), the columns are in the order a,
        b, c, d, e, where these coefficients make up the polynomial equation at^4 + bt^3 + ct^2 + dt
        + e = 0
    """
    n = p.shape[-1]
    A = np.zeros(p.shape[:1] + (n-1, n-1), float)
    A[...,1:,:-1] = np.eye(n-2)
    A[...,0,:] = -p[...,1:]/p[...,None,0]
    return np.linalg.eigvals(A)


def min_real_root(p, tol=1e-12):
    """Given an array of polynomial coefficients, find the minimum real root

    Parameters
    ==========
    p : array
        A mxn array of polynomial coefficients, where m is the number of equations and n-1 is the
        order of the polynomial. If n is 5 (4th order polynomial), the columns are in the order a,
        b, c, d, e, where these coefficients make up the polynomial equation at^4 + bt^3 + ct^2 + dt
        + e = 0
    tol : float, 1e-12
        Roots are considered if they have 

    Returns
    =======
    output : (time, index)
        `time` is the minimum real root from the set of polynomials, and `index` specifies the index
        of the responsible polynomial. i.e. the polynomial with the root `time` is p[index]
    """
    # Get the roots for the polynomials
    times = roots(p)

    # If the root has a nonzero imaginary component, set to infinity
    # If the root has a nonpositive real component, set to infinity
    times[(abs(times.imag) > tol) | (times.real <= tol)] = np.inf

    # now find the minimum time and the index of the responsible polynomial
    times = np.min(times.real, axis=1)

    return times.min(), times.argmin()


def unit_vector(vector, ord=None, handle_zero=False):
    """Returns the unit vector of the vector.

    Parameters
    ==========
    ord: None
        The type of normalization used. See
        https://numpy.org/doc/stable/reference/generated/numpy.linalg.norm.html
    handle_zero: bool, False
        If True and vector = <0,0,0>, <0,0,0> is returned.
    """
    if len(vector.shape) > 1:
        norm = np.linalg.norm(vector, ord=ord, axis=1, keepdims=True)
        if handle_zero:
            norm[(norm == 0).all(axis=1), :] = 1
        return vector / norm
    else:
        norm = np.linalg.norm(vector, ord=ord)
        if norm == 0 and handle_zero:
            norm = 1
        return vector / norm


def angle(v2, v1=(1,0)):
    """Calculates counter-clockwise angle of the projections of v1 and v2 onto the x-y plane"""
    ang = np.arctan2(v2[1], v2[0]) - np.arctan2(v1[1], v1[0])

    if ang < 0:
        return 2*np.pi + ang

    return ang


def coordinate_rotation(v, phi):
    """Rotate vector/matrix from one frame of reference to another (3D FIXME)"""

    rotation = np.array([[np.cos(phi), -np.sin(phi), 0],
                         [np.sin(phi),  np.cos(phi), 0],
                         [0          ,  0          , 1]])

    return np.matmul(rotation, v)


def solve_quartic(a, b, c, d, e):
    """Finds roots to ax**4 + bx**3 + cx**2 + d*x + e = 0

    FIXME broken, compare to np.roots for ground truth
    """

    delta0 = c**2 - 3*b*d + 12*a*e
    delta1 = 2*c**3 - 9*b*c*d + 27*b**2*e + 27*a*d**2 - 72*a*c*e
    delta = (4*delta0**3 - delta1**2)/27

    if delta != 0 and delta0 == 0:
        R = cmath.sqrt(-27*delta)
    else:
        R = delta1

    p = (8*a*c - 3*b**2)/8/a**2
    q = (b**3 - 4*a*b*c + 8*a**2*d)/8/a**3

    Q = ((delta1 + R)/2)**(1/3)
    S = 1/2 * cmath.sqrt(-2*p/3 + (Q + delta0/Q)/3/a)

    assert S != 0

    X = -b/4/a
    Y = -4*S**2 - 2*p
    Z = q/S

    return (
        X - S + 0.5*cmath.sqrt(Y + Z),
        X - S - 0.5*cmath.sqrt(Y + Z),
        X + S + 0.5*cmath.sqrt(Y - Z),
        X + S - 0.5*cmath.sqrt(Y - Z),
    )
