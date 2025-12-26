import numpy as np
from numba import jit

import pooltool.constants as const
import pooltool.ptmath as ptmath


@jit(nopython=True, cache=const.use_numba_cache)
def resolve_sphere_half_space_collision(normal, rvw, R, mu_k, e):
    rvw_f = rvw.copy()
    v_f = rvw_f[1]
    w_f = rvw_f[2]

    v_c = ptmath.surface_velocity(rvw, -normal, R)
    v_n_i, v_t_i, tangent = ptmath.decompose_normal_tangent(v_c, normal)
    has_relative_velocity = not np.isclose(v_t_i, 0.0)

    w_t_i = np.dot(rvw[1], tangent)

    D_v_n_magnitude = (1 + e) * -v_n_i
    D_v_n = D_v_n_magnitude * normal

    D_v_t_slip_magnitude = mu_k * D_v_n_magnitude
    D_v_t_slip_magnitude_squared = D_v_t_slip_magnitude**2
    D_v_t_slip = D_v_t_slip_magnitude * -tangent

    D_v_t_no_slip = (2.0 / 7.0) * (
        R * ptmath.cross(w_t_i * tangent, normal) - v_t_i * tangent
    )
    D_v_t_no_slip_magnitude_squared = ptmath.squared_norm3d(D_v_t_no_slip)

    if (
        not has_relative_velocity
        or D_v_t_no_slip_magnitude_squared <= D_v_t_slip_magnitude_squared
    ):
        v_f += D_v_n + D_v_t_no_slip
        w_f += (5.0 / 7.0) * (
            -w_t_i * tangent + ptmath.cross(normal, v_t_i * tangent) / R
        )
    else:
        v_f += D_v_n + D_v_t_slip
        w_f += (2.5 / R) * D_v_t_slip_magnitude * ptmath.cross(normal, tangent)

    return rvw_f
