#! /usr/bin/env python

import cmath
import numpy as np

from numba import njit
from scipy.spatial.transform import Rotation
from pyquaternion import Quaternion


def as_quaternion(w):
    N, D = w.shape
    quats = np.zeros((N, 4))

    for n in range(N):
        quat = Quaternion(axis=[1,0,0], angle=0)

        for d in range(D):
            if w[n,d] == 0:
                continue

            axis = np.zeros(D); axis[d] = 1
            quat *= Quaternion(axis=axis, angle=w[n,d])

        quats[n, :] = quat.normalised.elements

def as_quaternion(w):
    n = w.shape[0]
    quats = np.zeros((n, 4))
    for i in range(n):
        norm = np.linalg.norm(w[i,:])
        if norm == 0:
            quats[i, :] = np.array([1,0,0,0])
            continue
        quats[i, :] = Quaternion(axis=unit_vector(w[i,:]), angle=norm).normalised.elements
    return quats


def as_euler_angle(w):
    return Rotation.from_rotvec(w).as_euler('ZXY', degrees=True)


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

