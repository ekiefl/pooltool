"""This is a WIP"""

import math
from typing import Any, Dict, Tuple, TypeVar

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


def get_sin_and_cos_theta(h: float, R: float) -> Tuple[float, float]:
    """Returns sin(theta), cos(theta)"""
    sin_theta = (h - R) / R
    cos_theta = np.sqrt(1 - sin_theta**2)
    return sin_theta, cos_theta


def update_slip_speeds_and_angles(state: Dict[str, Any]) -> None:
    """
    Update the slip speeds and angles at the cushion (I) and table (C).
    """
    R = state["R"]
    sin_theta = state["sin_theta"]
    cos_theta = state["cos_theta"]
    vx = state["vx"]
    vy = state["vy"]
    omega_x = state["omega_x"]
    omega_y = state["omega_y"]
    omega_z = state["omega_z"]

    # Velocities at the cushion (I)
    v_xI = vx + omega_y * R * sin_theta - omega_z * R * cos_theta
    v_yI = -vy * sin_theta + omega_x * R

    # Velocities at the table (C)
    v_xC = vx - omega_y * R
    v_yC = vy + omega_x * R

    # Update slip speed and angle at the cushion (I)
    slip_speed = math.sqrt(v_xI**2 + v_yI**2)
    slip_angle = math.atan2(v_yI, v_xI)
    if slip_angle < 0:
        slip_angle += 2 * math.pi

    # Update slip speed and angle at the table (C)
    slip_speed_prime = math.sqrt(v_xC**2 + v_yC**2)
    slip_angle_prime = math.atan2(v_yC, v_xC)
    if slip_angle_prime < 0:
        slip_angle_prime += 2 * math.pi

    # Update state
    state["slip_speed"] = slip_speed
    state["slip_angle"] = slip_angle
    state["slip_speed_prime"] = slip_speed_prime
    state["slip_angle_prime"] = slip_angle_prime


def update_velocity(state: Dict[str, Any], delta_P: float) -> None:
    """
    Update the centroid velocity components.
    """
    mu_s = state["mu_s"]
    mu_w = state["mu_w"]
    M = state["M"]
    sin_theta = state["sin_theta"]
    cos_theta = state["cos_theta"]
    slip_angle = state["slip_angle"]
    slip_angle_prime = state["slip_angle_prime"]

    # Update vx
    state["vx"] -= (
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
    state["vy"] -= (
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


def update_angular_velocity(state: Dict[str, Any], delta_P: float) -> None:
    """
    Update the angular velocity components.
    """
    mu_s = state["mu_s"]
    mu_w = state["mu_w"]
    M = state["M"]
    R = state["R"]
    sin_theta = state["sin_theta"]
    cos_theta = state["cos_theta"]
    slip_angle = state["slip_angle"]
    slip_angle_prime = state["slip_angle_prime"]

    factor = 5 / (2 * M * R)

    state["omega_x"] += (
        -factor
        * (
            mu_w * math.sin(slip_angle)
            + mu_s
            * math.sin(slip_angle_prime)
            * (sin_theta + mu_w * math.sin(slip_angle) * cos_theta)
        )
        * delta_P
    )

    state["omega_y"] += (
        -factor
        * (
            mu_w * math.cos(slip_angle) * sin_theta
            - mu_s
            * math.cos(slip_angle_prime)
            * (sin_theta + mu_w * math.sin(slip_angle) * cos_theta)
        )
        * delta_P
    )

    state["omega_z"] += factor * (mu_w * math.cos(slip_angle) * cos_theta) * delta_P


def update_work_done(state: Dict[str, Any], delta_P: float) -> None:
    """
    Update the work done.
    """
    vy = state["vy"]
    cos_theta = state["cos_theta"]
    delta_WzI = delta_P * abs(vy) * cos_theta
    state["WzI"] += delta_WzI
    state["P"] += delta_P


def update_single_step(state: Dict[str, Any], delta_P: float) -> None:
    """
    Perform a single update step for the simulation.
    """
    update_slip_speeds_and_angles(state)
    update_velocity(state, delta_P)
    update_angular_velocity(state, delta_P)
    update_work_done(state, delta_P)

    state["i"] += 1
    if state["i"] > 10 * state["N"]:
        raise Exception("Solution not found")


def compression_phase(state: Dict[str, Any]) -> None:
    """
    Run the compression phase until the y-velocity is no longer positive.
    """
    delta_P = max((state["M"] * state["vy"]) / state["N"], 0.0001)
    while state["vy"] > 0:
        update_single_step(state, delta_P)


def restitution_phase(state: Dict[str, Any], target_work_rebound: float) -> None:
    """
    Run the restitution phase until the work at the cushion (WzI) reaches the target rebound work.
    """
    delta_P = max(target_work_rebound / state["N"], 0.0001)
    state["WzI"] = 0
    while state["WzI"] < target_work_rebound:
        update_single_step(state, delta_P)


def solve_paper(
    state: Dict[str, Any], v0: float, alpha: float, omega0S: float, omega0T: float
) -> None:
    """
    Convenience method that initializes the simulation parameters using polar components.
    """
    solve(
        state,
        v0 * math.cos(alpha),
        v0 * math.sin(alpha),
        -omega0T * math.sin(alpha),
        omega0T * math.cos(alpha),
        omega0S,
    )


def solve(
    state: Dict[str, Any],
    vx: float,
    vy: float,
    omega_x: float,
    omega_y: float,
    omega_z: float,
) -> None:
    """
    Initialize the state and run both the compression and restitution phases.
    """
    state["vx"] = vx
    state["vy"] = vy
    state["omega_x"] = omega_x
    state["omega_y"] = omega_y
    state["omega_z"] = omega_z

    state["WzI"] = 0
    state["P"] = 0
    state["i"] = 0

    compression_phase(state)
    target_work_rebound = state["ee"] ** 2 * state["WzI"]
    restitution_phase(state, target_work_rebound)


def create_mathavan_state(
    M: float, R: float, h: float, ee: float, mu_s: float, mu_w: float
) -> Dict[str, Any]:
    """
    Create a state dictionary for the Mathavan model with all required parameters.
    """
    sin_theta, cos_theta = get_sin_and_cos_theta(h, R)

    return {
        # Physical constants
        "M": M,
        "R": R,
        "h": h,
        "ee": ee,
        "mu_s": mu_s,
        "mu_w": mu_w,
        "sin_theta": sin_theta,
        "cos_theta": cos_theta,
        # Work and step counter
        "P": 0.0,
        "WzI": 0.0,
        "i": 0,
        "N": 5000,
        # Centroid velocity components
        "vx": 0.0,
        "vy": 0.0,
        # Angular velocity components
        "omega_x": 0.0,
        "omega_y": 0.0,
        "omega_z": 0.0,
        # Slip speeds and angles at cushion (I) and table (C)
        "slip_speed": 0.0,
        "slip_angle": 0.0,
        "slip_speed_prime": 0.0,
        "slip_angle_prime": 0.0,
    }


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
    state = create_mathavan_state(M, R, h, ee, ball.params.u_s, mu)
    solve(state, vx_rot, vy_rot, omega_x_rot, omega_y_rot, omega_z_rot)

    # Update the rotated state with the simulation's output.
    rvw_R[1, 0] = state["vx"]
    rvw_R[1, 1] = state["vy"]
    rvw_R[2, 0] = state["omega_x"]
    rvw_R[2, 1] = state["omega_y"]
    rvw_R[2, 2] = state["omega_z"]

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
