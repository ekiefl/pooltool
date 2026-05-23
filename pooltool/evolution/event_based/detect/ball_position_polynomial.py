import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.physics.utils import tangent_surface_velocity


@jit(nopython=True, cache=const.use_numba_cache)
def rva_to_xyz(r, v, a) -> NDArray[np.float64]:
    """
    Group position, velocity, acceleration vectors into xyz components
    """
    return np.array(
        [
            [r[0], v[0], a[0]],
            [r[1], v[1], a[1]],
            [r[2], v[2], a[2]],
        ]
    )


@jit(nopython=True, cache=const.use_numba_cache)
def ball_stationary_position_polynomial(rvw) -> NDArray[np.float64]:
    return rva_to_xyz(rvw[0], np.zeros(3), np.zeros(3))


@jit(nopython=True, cache=const.use_numba_cache)
def ball_rolling_position_polynomial(rvw, mu_rr, g) -> NDArray[np.float64]:
    return rva_to_xyz(
        rvw[0], rvw[1], 0.5 * mu_rr * g * -(rvw[1] / ptmath.norm3d(rvw[1]))
    )


@jit(nopython=True, cache=const.use_numba_cache)
def ball_sliding_position_polynomial(rvw, R, mu_s, g) -> NDArray[np.float64]:
    unit_z = np.array([0, 0, 1])
    v_hat_c_0 = tangent_surface_velocity(rvw, -unit_z, R)
    return rva_to_xyz(rvw[0], rvw[1], 0.5 * mu_s * g * -v_hat_c_0)


@jit(nopython=True, cache=const.use_numba_cache)
def ball_airborne_position_polynomial(rvw, g) -> NDArray[np.float64]:
    return rva_to_xyz(rvw[0], rvw[1], 0.5 * np.array([0, 0, -g]))


@jit(nopython=True, cache=const.use_numba_cache)
def ball_position_polynomial(
    s: int, rvw: NDArray[np.float64], R: float, mu_rr: float, mu_s: float, g: float
) -> NDArray[np.float64]:

    if s == const.stationary or s == const.spinning or s == const.pocketed:
        return ball_stationary_position_polynomial(rvw)
    elif s == const.rolling:
        return ball_rolling_position_polynomial(rvw, mu_rr, g)
    elif s == const.sliding:
        return ball_sliding_position_polynomial(rvw, R, mu_s, g)
    elif s == const.airborne:
        return ball_airborne_position_polynomial(rvw, g)

    raise ValueError("invalid state")
