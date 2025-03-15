"""This is a WIP"""

import math
from typing import NamedTuple, Tuple, TypeVar

import attrs
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
from pooltool.physics.resolve.models import BallCCushionModel, BallLCushionModel

# Type variable for cushion segments.
Cushion = TypeVar("Cushion", LinearCushionSegment, CircularCushionSegment)


class SlipState(NamedTuple):
    """
    Slip speeds and angles at cushion (I) and table (C).
    """

    slip_speed: float
    slip_angle: float
    slip_speed_prime: float
    slip_angle_prime: float


def get_sin_and_cos_theta(h: float, R: float) -> Tuple[float, float]:
    """Returns sin(theta), cos(theta)"""
    sin_theta = (h - R) / R
    cos_theta = np.sqrt(1 - sin_theta**2)
    return sin_theta, cos_theta


def calculate_slip_speeds_and_angles(
    R: float,
    sin_theta: float,
    cos_theta: float,
    vx: float,
    vy: float,
    omega_x: float,
    omega_y: float,
    omega_z: float,
) -> SlipState:
    """
    Calculate the slip speeds and angles at the cushion (I) and table (C).
    """
    # Velocities at the cushion (I)
    v_xI = vx + omega_y * R * sin_theta - omega_z * R * cos_theta
    v_yI = -vy * sin_theta + omega_x * R

    # Velocities at the table (C)
    v_xC = vx - omega_y * R
    v_yC = vy + omega_x * R

    # Calculate slip speed and angle at the cushion (I)
    slip_speed = math.sqrt(v_xI**2 + v_yI**2)
    slip_angle = math.atan2(v_yI, v_xI)
    if slip_angle < 0:
        slip_angle += 2 * math.pi

    # Calculate slip speed and angle at the table (C)
    slip_speed_prime = math.sqrt(v_xC**2 + v_yC**2)
    slip_angle_prime = math.atan2(v_yC, v_xC)
    if slip_angle_prime < 0:
        slip_angle_prime += 2 * math.pi

    return SlipState(
        slip_speed=slip_speed,
        slip_angle=slip_angle,
        slip_speed_prime=slip_speed_prime,
        slip_angle_prime=slip_angle_prime,
    )


def update_velocity(
    M: float,
    mu_s: float,
    mu_w: float,
    sin_theta: float,
    cos_theta: float,
    vx: float,
    vy: float,
    slip_angle: float,
    slip_angle_prime: float,
    delta_P: float,
) -> Tuple[float, float]:
    """
    Update the centroid velocity components.
    """
    # Update vx
    vx_new = vx - (
        (1 / M)
        * (
            mu_w * math.cos(slip_angle)
            + mu_s
            * math.cos(slip_angle_prime)
            * (sin_theta + mu_w * math.sin(slip_angle) * cos_theta)
        )
        * delta_P
    )

    # Update vy
    vy_new = vy - (
        (1 / M)
        * (
            cos_theta
            - mu_w * sin_theta * math.sin(slip_angle)
            + mu_s
            * math.sin(slip_angle_prime)
            * (sin_theta + mu_w * math.sin(slip_angle) * cos_theta)
        )
        * delta_P
    )

    return vx_new, vy_new


def update_angular_velocity(
    M: float,
    R: float,
    mu_s: float,
    mu_w: float,
    sin_theta: float,
    cos_theta: float,
    omega_x: float,
    omega_y: float,
    omega_z: float,
    slip_angle: float,
    slip_angle_prime: float,
    delta_P: float,
) -> Tuple[float, float, float]:
    """
    Update the angular velocity components.
    """
    factor = 5 / (2 * M * R)

    omega_x_new = omega_x + (
        -factor
        * (
            mu_w * math.sin(slip_angle)
            + mu_s
            * math.sin(slip_angle_prime)
            * (sin_theta + mu_w * math.sin(slip_angle) * cos_theta)
        )
        * delta_P
    )

    omega_y_new = omega_y + (
        -factor
        * (
            mu_w * math.cos(slip_angle) * sin_theta
            - mu_s
            * math.cos(slip_angle_prime)
            * (sin_theta + mu_w * math.sin(slip_angle) * cos_theta)
        )
        * delta_P
    )

    omega_z_new = omega_z + (
        factor * (mu_w * math.cos(slip_angle) * cos_theta) * delta_P
    )

    return omega_x_new, omega_y_new, omega_z_new


def calculate_work_done(vy: float, cos_theta: float, delta_P: float) -> float:
    """
    Calculate the work done for a single step.
    """
    return delta_P * abs(vy) * cos_theta


def compression_phase(
    M: float,
    R: float,
    mu_s: float,
    mu_w: float,
    sin_theta: float,
    cos_theta: float,
    vx: float,
    vy: float,
    omega_x: float,
    omega_y: float,
    omega_z: float,
    max_steps: int = 5000,
) -> Tuple[float, float, float, float, float, float]:
    """
    Run the compression phase until the y-velocity is no longer positive.

    Returns:
        Tuple of (vx, vy, omega_x, omega_y, omega_z, total_work)
    """
    WzI = 0.0
    step_count = 0

    # Calculate initial step size based on initial velocity
    delta_P = max((M * vy) / max_steps, 0.0001)

    while vy > 0:
        # Calculate slip states
        slip = calculate_slip_speeds_and_angles(
            R, sin_theta, cos_theta, vx, vy, omega_x, omega_y, omega_z
        )

        # Update velocities
        vx, vy = update_velocity(
            M,
            mu_s,
            mu_w,
            sin_theta,
            cos_theta,
            vx,
            vy,
            slip.slip_angle,
            slip.slip_angle_prime,
            delta_P,
        )

        omega_x, omega_y, omega_z = update_angular_velocity(
            M,
            R,
            mu_s,
            mu_w,
            sin_theta,
            cos_theta,
            omega_x,
            omega_y,
            omega_z,
            slip.slip_angle,
            slip.slip_angle_prime,
            delta_P,
        )

        # Calculate work for this step
        delta_WzI = calculate_work_done(vy, cos_theta, delta_P)
        WzI += delta_WzI

        # Update step count
        step_count += 1
        if step_count > 10 * max_steps:
            raise Exception("Solution not found in compression phase")

    return vx, vy, omega_x, omega_y, omega_z, WzI


def restitution_phase(
    M: float,
    R: float,
    mu_s: float,
    mu_w: float,
    sin_theta: float,
    cos_theta: float,
    vx: float,
    vy: float,
    omega_x: float,
    omega_y: float,
    omega_z: float,
    target_work_rebound: float,
    max_steps: int = 5000,
) -> Tuple[float, float, float, float, float]:
    """
    Run the restitution phase until the work at the cushion (WzI) reaches the target rebound work.

    Returns:
        Tuple of (vx, vy, omega_x, omega_y, omega_z)
    """
    WzI = 0.0
    step_count = 0

    # Calculate step size based on target work
    delta_P = max(target_work_rebound / max_steps, 0.0001)

    while WzI < target_work_rebound:
        # Calculate slip states
        slip = calculate_slip_speeds_and_angles(
            R, sin_theta, cos_theta, vx, vy, omega_x, omega_y, omega_z
        )

        # Update velocities
        vx, vy = update_velocity(
            M,
            mu_s,
            mu_w,
            sin_theta,
            cos_theta,
            vx,
            vy,
            slip.slip_angle,
            slip.slip_angle_prime,
            delta_P,
        )

        omega_x, omega_y, omega_z = update_angular_velocity(
            M,
            R,
            mu_s,
            mu_w,
            sin_theta,
            cos_theta,
            omega_x,
            omega_y,
            omega_z,
            slip.slip_angle,
            slip.slip_angle_prime,
            delta_P,
        )

        # Calculate work for this step
        delta_WzI = calculate_work_done(vy, cos_theta, delta_P)
        WzI += delta_WzI

        # Update step count
        step_count += 1
        if step_count > 10 * max_steps:
            raise Exception("Solution not found in restitution phase")

    return vx, vy, omega_x, omega_y, omega_z


def solve_paper(
    M: float,
    R: float,
    h: float,
    ee: float,
    mu_s: float,
    mu_w: float,
    v0: float,
    alpha: float,
    omega0S: float,
    omega0T: float,
) -> Tuple[float, float, float, float, float]:
    """
    Convenience method that solves using parameters common in research papers.

    Args:
        M: Mass of the ball
        R: Radius of the ball
        h: Height of the cushion
        ee: Coefficient of restitution
        mu_s: Sliding friction coefficient between ball and table
        mu_w: Sliding friction coefficient between ball and cushion
        v0: Initial speed
        alpha: Incident angle in radians
        omega0S: Initial sidespin angular velocity
        omega0T: Initial topspin angular velocity

    Returns:
        Tuple of (vx, vy, omega_x, omega_y, omega_z) after collision
    """
    return solve(
        M,
        R,
        h,
        ee,
        mu_s,
        mu_w,
        v0 * math.cos(alpha),
        v0 * math.sin(alpha),
        -omega0T * math.sin(alpha),
        omega0T * math.cos(alpha),
        omega0S,
    )


def solve(
    M: float,
    R: float,
    h: float,
    ee: float,
    mu_s: float,
    mu_w: float,
    vx: float,
    vy: float,
    omega_x: float,
    omega_y: float,
    omega_z: float,
) -> Tuple[float, float, float, float, float]:
    """
    Initialize the state and run both the compression and restitution phases.

    Args:
        M: Mass of the ball
        R: Radius of the ball
        h: Height of the cushion
        ee: Coefficient of restitution
        mu_s: Sliding friction coefficient between ball and table
        mu_w: Sliding friction coefficient between ball and cushion
        vx: Initial x-velocity
        vy: Initial y-velocity
        omega_x: Initial x-angular velocity
        omega_y: Initial y-angular velocity
        omega_z: Initial z-angular velocity

    Returns:
        Tuple of (vx, vy, omega_x, omega_y, omega_z) after collision
    """
    sin_theta, cos_theta = get_sin_and_cos_theta(h, R)

    # Run the compression phase
    vx, vy, omega_x, omega_y, omega_z, WzI = compression_phase(
        M, R, mu_s, mu_w, sin_theta, cos_theta, vx, vy, omega_x, omega_y, omega_z
    )

    # Calculate target work for rebound
    target_work_rebound = ee**2 * WzI

    # Run the restitution phase
    vx, vy, omega_x, omega_y, omega_z = restitution_phase(
        M,
        R,
        mu_s,
        mu_w,
        sin_theta,
        cos_theta,
        vx,
        vy,
        omega_x,
        omega_y,
        omega_z,
        target_work_rebound,
    )

    return vx, vy, omega_x, omega_y, omega_z


def solve_mathavan(ball: Ball, cushion: Cushion) -> Tuple[Ball, Cushion]:
    """
    Run the Mathavan model to simulate the ball-cushion collision.

    This version rotates the ball state into the cushion frame using the same coordinate
    transformation functions as Han2005. However, because the Mathavan simulation expects
    the collision approach to be along the positive y-axis, we rotate the state so that the
    cushion's normal (obtained via cushion.get_normal) maps to (0,1).
    """
    M = ball.params.m
    R = ball.params.R
    ee = ball.params.e_c  # cushion restitution coefficient
    mu = ball.params.f_c  # friction coefficient for both sliding modes
    u_s = ball.params.u_s  # sliding friction between ball and table

    h = cushion.height

    # Extract the ball state (assumed to be a NumPy array with rows:
    #  0: position, 1: translational velocity, 2: rotational velocity)
    rvw = ball.state.rvw

    # Get the cushion's normal vector (assumed to lie in the table plane).
    normal = cushion.get_normal(rvw)
    # Ensure the normal is pointing in the same direction as the ball's velocity.
    if np.dot(normal, rvw[1]) <= 0:
        normal = -normal

    # Compute the angle (psi) of the cushion normal in the table frame.
    psi = ptmath.angle(normal)
    # Determine the rotation angle that maps the cushion normal to (0,1).
    angle_to_rotate = (math.pi / 2) - psi

    # Rotate the ball's state into the cushion frame.
    rvw_R = ptmath.coordinate_rotation(rvw.T, angle_to_rotate).T

    # Extract rotated velocity components.
    vx_rot = rvw_R[1, 0]
    vy_rot = rvw_R[1, 1]
    omega_x_rot = rvw_R[2, 0]
    omega_y_rot = rvw_R[2, 1]
    omega_z_rot = rvw_R[2, 2]

    # Run the Mathavan simulation in the cushion frame.
    vx_final, vy_final, omega_x_final, omega_y_final, omega_z_final = solve(
        M, R, h, ee, u_s, mu, vx_rot, vy_rot, omega_x_rot, omega_y_rot, omega_z_rot
    )

    # Update the rotated state with the simulation's output.
    rvw_R[1, 0] = vx_final
    rvw_R[1, 1] = vy_final
    rvw_R[2, 0] = omega_x_final
    rvw_R[2, 1] = omega_y_final
    rvw_R[2, 2] = omega_z_final

    # Rotate the state back to the table frame.
    rvw_final = ptmath.coordinate_rotation(rvw_R.T, -angle_to_rotate).T

    ball.state = BallState(rvw_final, const.sliding)
    return ball, cushion


@attrs.define
class Mathavan2010Linear(CoreBallLCushionCollision):
    model: BallLCushionModel = attrs.field(
        default=BallLCushionModel.MATHAVAN_2010, init=False, repr=False
    )

    def solve(
        self, ball: Ball, cushion: LinearCushionSegment
    ) -> Tuple[Ball, LinearCushionSegment]:
        return solve_mathavan(ball, cushion)


@attrs.define
class Mathavan2010Circular(CoreBallCCushionCollision):
    model: BallCCushionModel = attrs.field(
        default=BallCCushionModel.MATHAVAN_2010, init=False, repr=False
    )

    def solve(
        self, ball: Ball, cushion: CircularCushionSegment
    ) -> Tuple[Ball, CircularCushionSegment]:
        return solve_mathavan(ball, cushion)
