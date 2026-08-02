import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const


@jit(nopython=True, cache=const.use_numba_cache)
def parabola_sphere_distance_quartic_coefficients(
    xyz: NDArray[np.float64],
    distance: float,
) -> NDArray[np.float64]:
    """Quartic coefficients for a parabolic trajectory being a fixed distance from the origin.

    The trajectory is a 3D parametric parabola ``r(t) = r0 + r1 * t + r2 * t**2``,
    with the per-axis coefficients given by the rows of ``xyz``. The times ``t`` at
    which ``r(t)`` is exactly ``distance`` from the origin are the roots of

        f(t) = (|r(t)|**2 - distance**2) / 2

    which is a quartic in ``t``. This returns its five coefficients.

    Args:
        xyz:
            The parabola coefficients as a ``(3, 3)`` array. Row ``i`` holds the
            ``(constant, linear, quadratic)`` coefficients of axis ``i``, so that
            axis ``i`` traces ``xyz[i, 0] + xyz[i, 1] * t + xyz[i, 2] * t**2``. For
            ball-ball detection this is the relative position polynomial of the two
            ball centers.
        distance:
            The target separation from the origin. For ball-ball detection this is
            the sum of the two ball radii (the contact distance).
    """
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
    """Quartic coefficients for a 2D parabolic trajectory being a fixed distance from a circle.

    The 2D analogue of :func:`parabola_sphere_distance_quartic_coefficients`. The
    trajectory is a 2D parametric parabola ``r(t) = r0 + r1 * t + r2 * t**2``, with
    the per-axis coefficients given by the rows of ``xy``. The times ``t`` at which
    ``r(t)`` is exactly ``radius`` from ``center`` are the roots of

        f(t) = (|r(t) - center|**2 - radius**2) / 2

    which is a quartic in ``t``. This returns its five coefficients. For
    linear-cushion detection the trajectory is the ball center projected into the
    plane perpendicular to the cushion axis, and the circle is the cross-section of
    the cushion nose cylinder.

    Args:
        xy:
            The parabola coefficients as a ``(2, 3)`` array. Row ``i`` holds the
            ``(constant, linear, quadratic)`` coefficients of axis ``i``, so that
            axis ``i`` traces ``xy[i, 0] + xy[i, 1] * t + xy[i, 2] * t**2``.
        center:
            The ``(x, y)`` coordinates of the circle center.
        radius:
            The target separation from ``center``. For linear-cushion detection
            this is the cushion nose radius plus the ball radius (the contact
            distance).
    """
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
