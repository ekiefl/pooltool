#! /usr/bin/env python
import numpy as np

def unit_vector(vector):
    """Returns the unit vector of the vector."""
    return vector / np.linalg.norm(vector)


def angle(v2, v1=(1,0)):
    """Calculates counter-clockwise angle of the projections of v1 and v2 onto the x-y plane"""

    ang2 = np.arctan2(v2[1], v2[0])
    ang1 = np.arctan2(v1[1], v1[0])

    return ang2 - ang1


def coordinate_rotation(v, phi):
    """Convert vector from one frame of reference to another (3D FIXME)"""

    rotation = np.array([[np.cos(phi), -np.sin(phi), 0],
                         [np.sin(phi),  np.cos(phi), 0],
                         [0          ,  0          , 1]])

    return np.matmul(rotation, v)
