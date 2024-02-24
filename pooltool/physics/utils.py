import numpy as np
from numba import jit

import pooltool.constants as const
import pooltool.ptmath as ptmath


@jit(nopython=True, cache=const.use_numba_cache)
def rel_velocity(rvw, R):
    """Compute velocity of cloth with respect to ball's point of contact

    This vector is non-zero whenever the ball is sliding
    """
    _, v, w = rvw
    return v + R * ptmath.cross(np.array([0.0, 0.0, 1.0], dtype=np.float64), w)


@jit(nopython=True, cache=const.use_numba_cache)
def get_u_vec(rvw, phi, R, s):
    if s == const.rolling:
        return np.array([1.0, 0.0, 0.0])

    rel_vel = rel_velocity(rvw, R)

    if (rel_vel == 0.0).all():
        return np.array([1.0, 0.0, 0.0])

    return ptmath.coordinate_rotation(ptmath.unit_vector(rel_vel), -phi)


@jit(nopython=True, cache=const.use_numba_cache)
def get_slide_time(rvw, R, u_s, g):
    if u_s == 0.0:
        return np.inf

    return 2 * ptmath.norm3d(rel_velocity(rvw, R)) / (7 * u_s * g)


@jit(nopython=True, cache=const.use_numba_cache)
def get_roll_time(rvw, u_r, g):
    if u_r == 0.0:
        return np.inf

    _, v, _ = rvw
    return ptmath.norm3d(v) / (u_r * g)


@jit(nopython=True, cache=const.use_numba_cache)
def get_spin_time(rvw, R, u_sp, g):
    if u_sp == 0.0:
        return np.inf

    _, _, w = rvw
    return np.abs(w[2]) * 2 / 5 * R / u_sp / g


def get_ball_energy(rvw, R, m):
    """Get the energy of a ball

    Currently calculating linear and rotational kinetic energy. Need to add potential
    energy if z-axis is freed
    """
    # Linear
    LKE = m * ptmath.norm3d(rvw[1]) ** 2 / 2

    # Rotational
    I = 2 / 5 * m * R**2
    RKE = I * ptmath.norm3d(rvw[2]) ** 2 / 2

    return LKE + RKE


def is_overlapping(rvw1, rvw2, R1, R2):
    return ptmath.norm3d(rvw1[0] - rvw2[0]) < (R1 + R2)
