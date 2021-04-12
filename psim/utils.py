#! /usr/bin/env python

import time
import cmath
import datetime
import numpy as np

from numba import njit
from collections import OrderedDict

def unit_vector(vector):
    """Returns the unit vector of the vector."""
    return vector / np.linalg.norm(vector)


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


class Timer:
    """Manages an ordered dictionary, where each key is a checkpoint name and value is a timestamp"""

    def __init__(self, initial_checkpoint_key=0):
        self.timer_start = self.timestamp()
        self.initial_checkpoint_key = initial_checkpoint_key
        self.last = self.initial_checkpoint_key
        self.checkpoints = OrderedDict([(initial_checkpoint_key, self.timer_start)])
        self.num_checkpoints = 0


    def timestamp(self):
        return datetime.datetime.fromtimestamp(time.time())


    def elapsed_time(self, as_timedelta=False):
        return self.timedelta_to_checkpoint(self.timestamp()).total_seconds()


    def timedelta_to_checkpoint(self, timestamp=None, checkpoint_key=None):
        if not timestamp: timestamp = self.timestamp()
        if not checkpoint_key: checkpoint_key = self.initial_checkpoint_key
        if checkpoint_key not in self.checkpoints: return datetime.timedelta(weeks=52)
        timedelta = timestamp - self.checkpoints[checkpoint_key]
        return timedelta


    def time_between_checkpoints(self, key2, key1, as_timedelta=False):
        """Find time difference between two checkpoints in seconds"""

        time_diff = self.timedelta_to_checkpoint(self.checkpoints[key2], key1)
        return time_diff if as_timedelta else time_diff.total_seconds()


    def make_checkpoint(self, checkpoint_key=None, overwrite=False):
        if not checkpoint_key:
            checkpoint_key = self.num_checkpoints + 1

        if checkpoint_key in self.checkpoints:
            if not overwrite:
                raise ValueError('Timer.make_checkpoint :: %s already exists as a checkpoint key. '
                                 'All keys must be unique unless overwrite is set to True' % (str(checkpoint_key)))
        else:
            self.num_checkpoints += 1

        checkpoint = self.timestamp()

        self.checkpoints[checkpoint_key] = checkpoint
        self.last = checkpoint_key

        return checkpoint


class TimeCode(object):
    """Time a block of code.
    This context manager times blocks of code.
    Examples
    ========
    >>> import time
    >>> import maple.utils as utils
    >>> # EXAMPLE 1
    >>> with utils.TimeCode() as t:
    >>>     time.sleep(5)
    ✓ Code finished successfully after 05s
    >>> # EXAMPLE 2
    >>> with terminal.TimeCode() as t:
    >>>     time.sleep(5)
    >>>     print(asdf) # undefined variable
    ✖ Code encountered error after 05s
    >>> # EXAMPLE 3
    >>> with terminal.TimeCode(quiet=True) as t:
    >>>     time.sleep(5)
    >>> print(t.time)
    0:00:05.000477
    """

    def __init__(self, quiet=False):
        self.s_msg = '✓ Code finished after'
        self.f_msg = '✖ Code encountered error after'
        self.quiet = quiet


    def __enter__(self):
        self.timer = Timer()
        return self


    def __exit__(self, exception_type, exception_value, traceback):
        self.time = self.timer.timedelta_to_checkpoint(self.timer.timestamp())
        return_code = 0 if exception_type is None else 1

        if not self.quiet:
            if return_code == 0:
                print(f"{self.s_msg} {self.time}")
            else:
                print(f"{self.f_msg} {self.time}")
