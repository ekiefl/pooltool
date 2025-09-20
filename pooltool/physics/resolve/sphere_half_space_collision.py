import numpy as np
import quaternion
from numba import jit

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.physics.utils import tangent_surface_velocity


def resolve_sphere_half_space_collision(normal, rvw, R, mu_k, e):
    unit_z = np.array([0.0, 0.0, 1.0])
    frame_rotation = ptmath.quaternion_from_vector_to_vector(normal, unit_z)
    rvw = quaternion.rotate_vectors(frame_rotation, rvw)
    rvw = resolve_sphere_half_space_collision_z_normal(rvw=rvw, R=R, mu_k=mu_k, e=e)
    rvw = quaternion.rotate_vectors(frame_rotation.conjugate(), rvw)
    return rvw


@jit(nopython=True, cache=const.use_numba_cache)
def resolve_sphere_half_space_collision_z_normal(rvw, R, mu_k, e):
    unit_z = np.array([0.0, 0.0, 1.0])

    v_i = rvw[1]
    w_i = rvw[2]

    rvw_f = rvw.copy()
    v_f = rvw_f[1]
    w_f = rvw_f[2]

    assert v_i[2] < 0

    D_v_perpendicular_magnitude = (1 + e) * -v_i[2]
    D_v_perpendicular = np.array([0, 0, D_v_perpendicular_magnitude])

    # discard velocity normal components
    v_i[2] = 0.0
    w_i[2] = 0.0

    v_c_i = tangent_surface_velocity(rvw, -unit_z, R)
    v_c_i_magnitude = ptmath.norm3d(v_c_i)

    has_relative_velocity = v_c_i_magnitude > const.EPS
    if has_relative_velocity:
        v_hat_c_i = v_c_i / v_c_i_magnitude
        D_v_parallel_slip = mu_k * D_v_perpendicular_magnitude * -v_hat_c_i
    else:
        v_hat_c_i = np.zeros(3)
        D_v_parallel_slip = np.zeros(3)

    D_v_parallel_no_slip = (2.0 / 7.0) * (R * ptmath.cross(w_i, unit_z) - v_i)

    if not has_relative_velocity or ptmath.squared_norm3d(
        D_v_parallel_no_slip
    ) <= ptmath.squared_norm3d(D_v_parallel_slip):
        v_f += D_v_perpendicular + D_v_parallel_no_slip
        w_f += (5.0 / 7.0) * (-w_i + ptmath.cross(unit_z, v_i) / R)
    else:
        v_f += D_v_perpendicular + D_v_parallel_slip
        w_f += (
            (2.5 / R)
            * ptmath.norm3d(D_v_parallel_slip)
            * ptmath.cross(unit_z, v_hat_c_i)
        )

    return rvw_f
