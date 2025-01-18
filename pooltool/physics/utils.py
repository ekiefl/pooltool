import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const
from pooltool.ptmath.utils import coordinate_rotation, cross, norm3d, unit_vector


@jit(nopython=True, cache=const.use_numba_cache)
def surface_velocity(
    rvw: NDArray[np.float64], d: NDArray[np.float64], R: float
) -> NDArray[np.float64]:
    """Compute velocity of a point on ball's surface (specified by unit direction vector)"""
    _, v, w = rvw
    return v + cross(w, R * d)


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
def get_airborne_time(rvw: NDArray[np.float64], R: float, g: float) -> float:
    if g == 0.0:
        return np.inf

    A = -0.5 * g
    B = rvw[1, 2]
    C = rvw[0, 2] - R

    D = B**2 - 4 * A * C

    if D < 0:
        # Only consider real roots.
        return np.inf

    # This is the only possible root assuming the ball starts above the table and
    # acceleration due to gravity is towards table.
    t_f = -(B + np.sqrt(D)) / (2 * A)

    return t_f


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


def on_table(rvw: NDArray[np.float64], R: float) -> float:
    return rvw[0, 2] == R


def get_ball_energy(rvw: NDArray[np.float64], R: float, m: float, g: float) -> float:
    """Get the energy of a ball

    Accounts for linear and rotational kinetic energy and potential energy due to gravity relative to a ball in contact with the table
    """
    # Linear
    LKE = m * norm3d(rvw[1]) ** 2 / 2

    # Rotational
    RKE = (2 / 5 * m * R**2) * norm3d(rvw[2]) ** 2 / 2

    # Potential
    MGH = m * g * (rvw[0, 2] - R)

    return LKE + RKE + MGH
