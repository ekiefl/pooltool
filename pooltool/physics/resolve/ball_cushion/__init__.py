from typing import Tuple

import numpy as np

import pooltool.constants as const
import pooltool.math as math
from pooltool.objects.ball.datatypes import Ball, BallState
from pooltool.objects.table.components import (
    CircularCushionSegment,
    LinearCushionSegment,
)


def resolve_linear_ball_cushion(
    ball: Ball, cushion: LinearCushionSegment, inplace: bool = False
) -> Tuple[Ball, LinearCushionSegment]:
    if not inplace:
        ball = ball.copy()
        cushion = cushion.copy()

    rvw = ball.state.rvw
    normal = cushion.get_normal(rvw)

    rvw = _resolve_ball_linear_cushion_collision(
        rvw=rvw,
        normal=normal,
        p1=cushion.p1,
        p2=cushion.p2,
        R=ball.params.R,
        m=ball.params.m,
        h=cushion.height,
        e_c=ball.params.e_c,
        f_c=ball.params.f_c,
    )

    ball.state = BallState(rvw, const.sliding)

    return ball, cushion


def resolve_circular_ball_cushion(
    ball: Ball, cushion: CircularCushionSegment, inplace: bool = False
) -> Tuple[Ball, CircularCushionSegment]:
    if not inplace:
        ball = ball.copy()
        cushion = cushion.copy()

    rvw = ball.state.rvw
    normal = cushion.get_normal(rvw)

    rvw = _resolve_ball_circular_cushion_collision(
        rvw=rvw,
        normal=normal,
        center=cushion.center,
        radius=cushion.radius,
        R=ball.params.R,
        m=ball.params.m,
        h=cushion.height,
        e_c=ball.params.e_c,
        f_c=ball.params.f_c,
    )

    ball.state = BallState(rvw, const.sliding)

    return ball, cushion


def _resolve_ball_linear_cushion_collision(
    rvw, normal, p1, p2, R, m, h, e_c, f_c, spacer: bool = True
):
    """Resolve the ball linear cushion collision

    Args:
        spacer:
            A correction is made such that if the ball is not a distance R from the
            cushion, the ball is moved along the normal such that it is, at least to
            within float precision error. That's where this paramter comes in. If spacer
            is True, a small epsilon of additional distance (constants.EPS_SPACE) is put
            between them, ensuring the cushion and ball are separated post-resolution.
    """
    # orient the normal so it points away from playing surface
    normal = normal if np.dot(normal, rvw[1]) > 0 else -normal

    rvw = _resolve_ball_cushion_collision(rvw, normal, R, m, h, e_c, f_c)

    # Calculate the point on cushion line where contact should be made, then set the
    # z-component to match the ball's height
    c = math.point_on_line_closest_to_point(p1, p2, rvw[0])
    c[2] = rvw[0, 2]

    # Move the ball to meet the cushion
    correction = R - math.norm3d(rvw[0] - c) + (const.EPS_SPACE if spacer else 0.0)
    rvw[0] -= correction * normal

    return rvw


def _resolve_ball_cushion_collision(rvw, normal, R, m, h, e_c, f_c):
    """Inhwan Han (2005) 'Dynamics in Carom and Three Cushion Billiards'"""

    # Change from the table frame to the cushion frame. The cushion frame is defined by
    # the normal vector is parallel with <1,0,0>.
    psi = math.angle(normal)
    rvw_R = math.coordinate_rotation(rvw.T, -psi).T

    # The incidence angle--called theta_0 in paper
    phi = math.angle(rvw_R[1]) % (2 * np.pi)

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
    I = 2 / 5 * m * R**2
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
    rvw_R[2, 0] += -R / I * PY * np.sin(theta_a)
    rvw_R[2, 1] += R / I * (PX * np.sin(theta_a) - PZ * np.cos(theta_a))
    rvw_R[2, 2] += R / I * PY * np.cos(theta_a)

    # Change back to table reference frame
    rvw = math.coordinate_rotation(rvw_R.T, psi).T

    return rvw


def get_ball_cushion_restitution(rvw, e_c):
    """Get restitution coefficient dependent on ball state

    Parameters
    ==========
    rvw: np.array
        Assumed to be in reference frame such that <1,0,0> points
        perpendicular to the cushion, and in the direction away from the table

    Notes
    =====
    - https://essay.utwente.nl/59134/1/scriptie_J_van_Balen.pdf suggests a constant
      value of 0.85
    """

    return e_c
    return max([0.40, 0.50 + 0.257 * rvw[1, 0] - 0.044 * rvw[1, 0] ** 2])


def get_ball_cushion_friction(rvw, f_c):
    """Get friction coeffecient depend on ball state

    Parameters
    ==========
    rvw: np.array
        Assumed to be in reference frame such that <1,0,0> points
        perpendicular to the cushion, and in the direction away from the table
    """

    ang = math.angle(rvw[1])

    if ang > np.pi:
        ang = np.abs(2 * np.pi - ang)

    ans = f_c
    return ans


def _resolve_ball_circular_cushion_collision(
    rvw, normal, center, radius, R, m, h, e_c, f_c, spacer: bool = True
):
    """Resolve the ball linear cushion collision

    Args:
        spacer:
            A correction is made such that if the ball is not a distance R from the
            cushion, the ball is moved along the normal such that it is, at least to
            within float precision error. That's where this paramter comes in. If spacer
            is True, a small epsilon of additional distance (constants.EPS_SPACE) is put
            between them, ensuring the cushion and ball are separated post-resolution.
    """
    # orient the normal so it points away from playing surface
    normal = normal if np.dot(normal, rvw[1]) > 0 else -normal

    rvw = _resolve_ball_cushion_collision(rvw, normal, R, m, h, e_c, f_c)

    c = np.array([center[0], center[1], rvw[0, 2]])
    correction = (
        R + radius - math.norm3d(rvw[0] - c) - (const.EPS_SPACE if spacer else 0.0)
    )

    rvw[0] += correction * normal

    return rvw
