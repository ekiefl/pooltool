from typing import Tuple, TypeVar

import numpy as np

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball, BallState
from pooltool.objects.table.components import (
    CircularCushionSegment,
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


def han2005(rvw, normal, R, m, h, e_c, f_c):
    """Inhwan Han (2005) 'Dynamics in Carom and Three Cushion Billiards'"""
    # orient the normal so it points away from playing surface
    normal = normal if np.dot(normal, rvw[1]) > 0 else -normal

    # Change from the table frame to the cushion frame. The cushion frame is defined by
    # the normal vector is parallel with <1,0,0>.
    psi = ptmath.angle(normal)
    rvw_R = ptmath.coordinate_rotation(rvw.T, -psi).T

    # The incidence angle--called theta_0 in paper
    phi = ptmath.angle(rvw_R[1]) % (2 * np.pi)

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
    c = rvw_R[1, 0] * np.cos(theta_a)  # 2D assumption

    # Eqs 16
    II = 2 / 5 * m * R**2
    A = 7 / 2 / m
    B = 1 / m

    # Eqs 17 & 20
    PzE = (1 + e) * c / B
    PzS = np.sqrt(sx**2 + sy**2) / A

    if PzS <= PzE:
        # Sliding and sticking case
        PX = -sx / A * np.sin(theta_a) - (1 + e) * c / B * np.cos(theta_a)
        PY = sy / A
        PZ = sx / A * np.cos(theta_a) - (1 + e) * c / B * np.sin(theta_a)
    else:
        # Forward sliding case
        PX = -mu * (1 + e) * c / B * np.cos(phi) * np.sin(theta_a) - (
            1 + e
        ) * c / B * np.cos(theta_a)
        PY = mu * (1 + e) * c / B * np.sin(phi)
        PZ = mu * (1 + e) * c / B * np.cos(phi) * np.cos(theta_a) - (
            1 + e
        ) * c / B * np.sin(theta_a)

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


Cushion = TypeVar("Cushion", LinearCushionSegment, CircularCushionSegment)


def _solve(ball: Ball, cushion: Cushion) -> Tuple[Ball, Cushion]:
    rvw = han2005(
        rvw=ball.state.rvw,
        normal=cushion.get_normal(ball.state.rvw),
        R=ball.params.R,
        m=ball.params.m,
        h=cushion.height,
        e_c=ball.params.e_c,
        f_c=ball.params.f_c,
    )

    ball.state = BallState(rvw, const.sliding)

    return ball, cushion


class Han2005Linear(CoreBallLCushionCollision):
    def solve(
        self, ball: Ball, cushion: LinearCushionSegment
    ) -> Tuple[Ball, LinearCushionSegment]:
        return _solve(ball, cushion)


class Han2005Circular(CoreBallCCushionCollision):
    def solve(
        self, ball: Ball, cushion: CircularCushionSegment
    ) -> Tuple[Ball, CircularCushionSegment]:
        return _solve(ball, cushion)
