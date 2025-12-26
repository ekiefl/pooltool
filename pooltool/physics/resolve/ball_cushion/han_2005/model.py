import attrs
import numpy as np

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball, BallState
from pooltool.objects.table.components import (
    CircularCushionSegment,
    Cushion,
    LinearCushionSegment,
)
from pooltool.physics.resolve.ball_cushion.core import (
    CoreBallCCushionCollision,
    CoreBallLCushionCollision,
)
from pooltool.physics.resolve.ball_cushion.han_2005.properties import (
    get_ball_cushion_friction,
    get_ball_cushion_restitution,
)
from pooltool.physics.resolve.models import BallCCushionModel, BallLCushionModel


def han2005(rvw, xy_normal, R, m, h, e_c, f_c):
    """Inhwan Han (2005) 'Dynamics in Carom and Three Cushion Billiards'"""

    # Change from the table frame to the cushion frame. The cushion frame is defined by
    # the normal vector is parallel with <1,0,0>.
    psi = ptmath.angle(xy_normal)
    rvw_R = ptmath.coordinate_rotation(rvw.T, -psi).T

    assert rvw_R[1, 0] > 0
    assert np.isclose(rvw_R[1, 2], 0)

    # Get mu and e
    e = get_ball_cushion_restitution(rvw_R, e_c)
    mu = get_ball_cushion_friction(rvw_R, f_c)

    # Depends on height of cushion relative to ball
    theta_a = np.arcsin(h / R - 1)

    # Eqs 14
    sx = rvw_R[1, 0] * np.sin(theta_a) - rvw_R[1, 2] * np.cos(theta_a) + R * rvw_R[2, 1]
    sy = (
        -rvw_R[1, 1]
        - R * rvw_R[2, 2] * np.cos(theta_a)
        + R * rvw_R[2, 0] * np.sin(theta_a)
    )
    c = -rvw_R[1, 0] * np.cos(theta_a)  # 2D assumption

    # Eqs 16
    II = 2 / 5 * m * R**2
    A = 7 / 2 / m
    B = 1 / m

    # Eqs 17 & 20
    PzE = -(1 + e) * c / B
    abs_s_0 = np.sqrt(sx**2 + sy**2)
    PzS = abs_s_0 / A

    if PzS <= mu * PzE:
        # Eqs 18 Sliding and sticking case
        PxE = sx / A
        PyE = sy / A
    else:
        # Eqs 19 Forward sliding case
        PxE = mu * PzE * sx / abs_s_0
        PyE = mu * PzE * sy / abs_s_0

    # Eqs 21 & 22 (transform P from contact normal coordinate frame to rail coordinate frame)
    PX = -PxE * np.sin(theta_a) - PzE * np.cos(theta_a)
    PY = PyE
    PZ = PxE * np.cos(theta_a) - PzE * np.sin(theta_a)

    # Eqs 23
    # Update velocity
    rvw_R[1, 0] += PX / m
    rvw_R[1, 1] += PY / m
    # rvw_R[1,2] += PZ/m

    # Update angular velocity
    rvw_R[2, 0] += -R / II * PY * np.sin(theta_a)
    rvw_R[2, 1] += R / II * (PX * np.sin(theta_a) - PZ * np.cos(theta_a))
    rvw_R[2, 2] += R / II * PY * np.cos(theta_a)

    # Change back to table reference frame
    rvw = ptmath.coordinate_rotation(rvw_R.T, psi).T

    return rvw


def _solve(ball: Ball, cushion: Cushion) -> tuple[Ball, Cushion]:
    xy_normal = cushion.get_normal_xy(ball.xyz)
    xy_normal = xy_normal if np.dot(xy_normal, ball.vel) > 0 else -xy_normal
    rvw = han2005(
        rvw=ball.state.rvw,
        xy_normal=xy_normal,
        R=ball.params.R,
        m=ball.params.m,
        h=cushion.height,
        e_c=ball.params.e_c,
        f_c=ball.params.f_c,
    )

    ball.state = BallState(rvw, const.sliding)

    return ball, cushion


@attrs.define
class Han2005Linear(CoreBallLCushionCollision):
    model: BallLCushionModel = attrs.field(
        default=BallLCushionModel.HAN_2005, init=False, repr=False
    )

    def solve(
        self, ball: Ball, cushion: LinearCushionSegment
    ) -> tuple[Ball, LinearCushionSegment]:
        return _solve(ball, cushion)


@attrs.define
class Han2005Circular(CoreBallCCushionCollision):
    model: BallCCushionModel = attrs.field(
        default=BallCCushionModel.HAN_2005, init=False, repr=False
    )

    def solve(
        self, ball: Ball, cushion: CircularCushionSegment
    ) -> tuple[Ball, CircularCushionSegment]:
        return _solve(ball, cushion)
