import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const


@jit(nopython=True, cache=const.use_numba_cache)
def parabola_sphere_distance_quartic_coefficients(
    xyz: NDArray[np.float64],
    distance: float,
) -> NDArray[np.float64]:

    x = xyz[0]
    y = xyz[1]
    z = xyz[2]

    xx = np.square(x)
    yy = np.square(y)
    zz = np.square(z)

    return np.array(
        [
            (xx[0] + yy[0] + zz[0] - distance * distance) / 2,
            x[1] * x[0] + y[1] * y[0] + z[1] * z[0],
            x[2] * x[0] + y[2] * y[0] + z[2] * z[0] + (xx[1] + yy[1] + zz[1]) / 2,
            x[2] * x[1] + y[2] * y[1] + z[2] * z[1],
            (xx[2] + yy[2] + zz[2]) / 2,
        ]
    )


@jit(nopython=True, cache=const.use_numba_cache)
def parabola_circle_distance_2d_quartic_coefficients(
    xy: NDArray[np.float64],
    center: NDArray[np.float64],
    radius: float,
) -> NDArray[np.float64]:

    x = xy[0]
    y = xy[1]

    C_x = x[0] - center[0]
    C_y = y[0] - center[1]
    return np.array(
        [
            (C_x * C_x + C_y * C_y - radius * radius) / 2,
            x[1] * C_x + y[1] * C_y,
            x[2] * C_x + y[2] * C_y + (x[1] * x[1] + y[1] * y[1]) / 2,
            x[2] * x[1] + y[2] * y[1],
            (x[2] * x[2] + y[2] * y[2]) / 2,
        ]
    )
