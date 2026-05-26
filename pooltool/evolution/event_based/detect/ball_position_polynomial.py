import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.physics.utils import tangent_surface_velocity


@jit(nopython=True, cache=const.use_numba_cache)
def ball_position_polynomial(
    s: int, rvw: NDArray[np.float64], R: float, mu_rr: float, mu_s: float, g: float
) -> NDArray[np.float64]:

    p: NDArray[np.float64] = np.empty((3, 3), dtype=np.float64)
    p[0] = rvw[0]
    p[1] = rvw[1]

    if s == const.stationary or s == const.spinning or s == const.pocketed:
        p[2] = np.zeros(3)
    elif s == const.rolling:
        p[2] = 0.5 * mu_rr * g * -(rvw[1] / ptmath.norm3d(rvw[1]))
    elif s == const.sliding:
        unit_z = np.array([0, 0, 1])
        v_hat_c_0 = tangent_surface_velocity(rvw, -unit_z, R)
        p[2] = 0.5 * mu_s * g * -v_hat_c_0
    elif s == const.airborne:
        p[2] = 0.5 * np.array([0, 0, -g])
    else:
        raise ValueError("invalid state")

    return p
