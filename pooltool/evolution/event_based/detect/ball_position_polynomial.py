import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.physics.utils import tangent_surface_velocity


@jit(nopython=True, cache=const.use_numba_cache)
def ball_position_polynomial(
    s: int, rvw: NDArray[np.float64], R: float, u_r: float, u_s: float, g: float
) -> NDArray[np.float64]:
    """Build the position-vs-time polynomial for a ball.

    The trajectory is expressed as

        r(t) = r0   + V0   * t + 1/2 a * t**2
             = p[0] + p[1] * t + p[2]  * t**2

    where each row of the returned ``(3, 3)`` array is an ``(x, y, z)`` vector.

    Returns:
        A ``(3, 3)`` array ``p`` where rows are the coefficients of the
        position polynomial in increasing power of ``t``:

        * ``p[0]``: initial position (``rvw[0]``).
        * ``p[1]``: initial velocity (``rvw[1]``).
        * ``p[2]``: half the acceleration vector (the coefficient of ``t**2``, not
          the acceleration itself).
    """
    p: NDArray[np.float64] = np.empty((3, 3), dtype=np.float64)
    p[0] = rvw[0]
    p[1] = rvw[1]

    if s == const.stationary or s == const.spinning or s == const.pocketed:
        p[2] = np.zeros(3)
    elif s == const.rolling:
        p[2] = 0.5 * u_r * g * -(rvw[1] / ptmath.norm3d(rvw[1]))
    elif s == const.sliding:
        unit_z = np.array([0, 0, 1])
        v_c = tangent_surface_velocity(rvw, -unit_z, R)
        p[2] = 0.5 * u_s * g * -ptmath.unit_vector(v_c)
    elif s == const.airborne:
        p[2] = 0.5 * np.array([0, 0, -g])
    else:
        raise ValueError("'{s}' is an unknown motion state")

    return p
