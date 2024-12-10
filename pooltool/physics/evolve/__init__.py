"""Evolve ball motion.

FIXME My vision for this package is to be somewhat like pooltool/physics/resolve/ but
specifically for the evolution of rolling, sliding, and spinning ball motion states,
i.e. the equations of motion presented in

https://ekiefl.github.io/2020/04/24/pooltool-theory/#3-ball-with-arbitrary-spin

The code should be configurable and passed to `PhysicsEngine` in `physics/engine.py`,
just like the `Resolver` class in `physics/resolve/resolver.py`
"""

import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const
import pooltool.ptmath as ptmath


@jit(nopython=True, cache=const.use_numba_cache)
def evolve_ball_motion(
    state: int,
    rvw: NDArray[np.float64],
    R: float,
    m: float,
    u_s: float,
    u_sp: float,
    u_r: float,
    g: float,
    t: float,
) -> NDArray[np.float64]:
    """Evolve ball motion.

    This function delegates to different equations of motion depending on the state passed.

    Important:
        This function does not evolve through event transitions. For example, if a
        sliding ball is destined to start rolling after 1 second, but you evolve the
        ball with this function for 2 seconds, an unrealistic trajectory will occur.
    """
    if state == const.stationary or state == const.pocketed:
        return rvw
    elif state == const.sliding:
        return evolve_slide_state(rvw, R, m, u_s, u_sp, g, t)
    elif state == const.rolling:
        return evolve_roll_state(rvw, R, u_r, u_sp, g, t)
    elif state == const.spinning:
        return evolve_perpendicular_spin_state(rvw, R, u_sp, g, t)
    elif state == const.airborne:
        return evolve_airborne_state(rvw, g, t)

    raise NotImplementedError()


@jit(nopython=True, cache=const.use_numba_cache)
def evolve_slide_state(
    rvw: NDArray[np.float64],
    R: float,
    m: float,
    u_s: float,
    u_sp: float,
    g: float,
    t: float,
) -> NDArray[np.float64]:
    if t == 0:
        return rvw

    v0z = rvw[1, 2]
    assert v0z == 0, f"Rolling ball can't have non-zero z-component velocity: {v0z}"

    # Angle of initial velocity in table frame
    phi = ptmath.angle(rvw[1])

    rvw_B0 = ptmath.coordinate_rotation(rvw.T, -phi).T

    # Relative velocity unit vector in ball frame
    u_0 = ptmath.coordinate_rotation(
        ptmath.unit_vector(ptmath.rel_velocity(rvw, R)), -phi
    )

    # Calculate quantities according to the ball frame. NOTE w_B in this code block
    # is only accurate of the x and y evolution of angular velocity. z evolution of
    # angular velocity is done in the next block

    rvw_B = np.empty((3, 3), dtype=np.float64)
    rvw_B[0, 0] = rvw_B0[1, 0] * t - 0.5 * u_s * g * t**2 * u_0[0]
    rvw_B[0, 1] = -0.5 * u_s * g * t**2 * u_0[1]
    rvw_B[0, 2] = 0
    rvw_B[1, :] = rvw_B0[1] - u_s * g * t * u_0
    rvw_B[2, :] = rvw_B0[2] - 5 / 2 / R * u_s * g * t * ptmath.cross(
        u_0, np.array([0, 0, 1], dtype=np.float64)
    )

    # This transformation governs the z evolution of angular velocity
    rvw_B[2, 2] = rvw_B0[2, 2]
    rvw_B = evolve_perpendicular_spin_state(rvw_B, R, u_sp, g, t)

    # Rotate to table reference
    rvw_T = ptmath.coordinate_rotation(rvw_B.T, phi).T
    rvw_T[0] += rvw[0]  # Add initial ball position

    return rvw_T


@jit(nopython=True, cache=const.use_numba_cache)
def evolve_roll_state(
    rvw: NDArray[np.float64], R: float, u_r: float, u_sp: float, g: float, t: float
) -> NDArray[np.float64]:
    if t == 0:
        return rvw

    r_0, v_0, _ = rvw

    v0z = v_0[2]
    assert v0z == 0, f"Rolling ball can't have non-zero z-component velocity: {v_0[2]}"

    v_0_hat = ptmath.unit_vector(v_0)

    r = r_0 + v_0 * t - 0.5 * u_r * g * t**2 * v_0_hat
    v = v_0 - u_r * g * t * v_0_hat
    w = ptmath.coordinate_rotation(v / R, np.pi / 2)

    # Independently evolve the z spin
    temp = evolve_perpendicular_spin_state(rvw, R, u_sp, g, t)

    w[2] = temp[2, 2]

    new_rvw = np.empty((3, 3), dtype=np.float64)
    new_rvw[0, :] = r
    new_rvw[1, :] = v
    new_rvw[2, :] = w

    return new_rvw


@jit(nopython=True, cache=const.use_numba_cache)
def evolve_perpendicular_spin_component(
    wz: float, R: float, u_sp: float, g: float, t: float
) -> float:
    if t == 0:
        return wz

    if np.abs(wz) < const.EPS:
        return wz

    alpha = 5 * u_sp * g / (2 * R)

    if t > np.abs(wz) / alpha:
        # You can't decay past 0 angular velocity
        t = np.abs(wz) / alpha

    # Always decay towards 0, whether spin is +ve or -ve
    sign = 1 if wz > 0 else -1

    wz_final = wz - sign * alpha * t
    return wz_final


@jit(nopython=True, cache=const.use_numba_cache)
def evolve_perpendicular_spin_state(
    rvw: NDArray[np.float64], R: float, u_sp: float, g: float, t: float
) -> NDArray[np.float64]:
    v0z = rvw[1, 2]
    assert v0z == 0, f"Spinning ball can't have non-zero z-component velocity: {v0z}"

    # Otherwise ball.state.rvw will be modified and corresponding entry in self.history
    # FIXME framework has changed, this may not be true. EDIT This is still true.
    rvw = rvw.copy()

    rvw[2, 2] = evolve_perpendicular_spin_component(rvw[2, 2], R, u_sp, g, t)
    return rvw


@jit(nopython=True, cache=const.use_numba_cache)
def evolve_airborne_state(
    rvw: NDArray[np.float64], g: float, t: float
) -> NDArray[np.float64]:
    if t == 0:
        return rvw

    r_0, v_0, w_0 = rvw

    g_vec = np.array([0.0, 0.0, g], dtype=np.float64)

    r = r_0 + v_0 * t - 0.5 * g_vec * t**2
    v = v_0 - g_vec * t

    new_rvw = np.empty((3, 3), dtype=np.float64)
    new_rvw[0, :] = r
    new_rvw[1, :] = v
    new_rvw[2, :] = w_0

    return new_rvw
