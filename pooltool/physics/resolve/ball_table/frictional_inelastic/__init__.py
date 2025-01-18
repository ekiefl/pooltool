import attrs
import numpy as np
from numba import jit
from numpy.typing import NDArray

import pooltool.constants as const
import pooltool.physics as physics
import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball, BallState
from pooltool.physics.resolve.ball_table.core import (
    CoreBallTableCollision,
    bounce_height,
    final_ball_motion_state,
)
from pooltool.physics.resolve.models import BallTableModel


@jit(nopython=True, cache=const.use_numba_cache)
def _resolve_ball_table(
    rvw: NDArray[np.float64], R: float, u: float, e: float
) -> NDArray[np.float64]:
    rvw_i = rvw.copy()
    v_i = rvw_i[1]
    w_i = rvw_i[2]
    if v_i[2] >= 0:
        raise ValueError(
            "Ball with non-negative z-velocity can't collide with table surface."
        )

    unit_z = np.array([0.0, 0.0, 1.0])

    D_v_perpendicular_magnitude = (1 + e) * -v_i[2]
    D_v_perpendicular = D_v_perpendicular_magnitude * unit_z

    # discard normal velocity
    v_i[2] = 0

    v_c_i = physics.surface_velocity(rvw_i, -unit_z, R)
    has_relative_velocity = ptmath.norm3d_squared(v_c_i) > const.EPS**2

    # if there is no relative surface velocity to begin with,
    # don't bother calculating slip condition
    if has_relative_velocity:
        v_hat_c_i = ptmath.unit_vector(v_c_i)
        D_v_parallel_slip = u * D_v_perpendicular_magnitude * -v_hat_c_i

    D_v_parallel_no_slip = (2.0 / 7.0) * (R * ptmath.cross(w_i, unit_z) - v_i)

    # if there was no relative velocity to begin with,
    # or if the impulse for the no-slip case is less than the impulse for the slip case
    # then slip condition is invalid so we use the results for the no-slip case
    if not has_relative_velocity or ptmath.norm3d_squared(
        D_v_parallel_no_slip
    ) <= ptmath.norm3d_squared(D_v_parallel_slip):
        rvw[1] = rvw[1] + D_v_perpendicular + D_v_parallel_no_slip
        rvw[2] = rvw[2] + (5.0 / 7.0) * (-w_i + ptmath.cross(unit_z, v_i) / R)
    else:
        rvw[1] = rvw[1] + D_v_perpendicular + D_v_parallel_slip
        rvw[2] = rvw[2] + (2.5 / R) * ptmath.norm3d(D_v_parallel_slip) * ptmath.cross(
            unit_z, v_hat_c_i
        )

    return rvw


@attrs.define
class FrictionalInelastic(CoreBallTableCollision):
    """A frictional, inelastic collision."""

    min_bounce_height: float = 0.005

    model: BallTableModel = attrs.field(
        default=BallTableModel.FRICTIONAL_INELASTIC, init=False, repr=False
    )

    def solve(self, ball: Ball) -> Ball:
        """Resolves the collision."""
        rvw = _resolve_ball_table(
            ball.state.rvw.copy(), ball.params.R, ball.params.u_s, ball.params.e_t
        )

        if bounce_height(rvw[1, 2], ball.params.g) < self.min_bounce_height:
            rvw[1, 2] = 0

        state = final_ball_motion_state(rvw, ball.params.R)

        ball.state = BallState(rvw, state)

        return ball
