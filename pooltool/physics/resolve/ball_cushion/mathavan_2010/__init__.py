import math
from typing import Tuple, TypeVar

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

# Fixed values for cushion contact point angles (assumes ball on table & fixed cushion height)
sin_theta = 2 / 5
cos_theta = math.sqrt(21) / 5


class Mathavan:
    """
    A simulation model for ball-cushion collisions based on the Mathavan model.
    This class implements the dynamics as described in your TypeScript code.
    """

    def __init__(self, M, R, ee, mu_s, mu_w):
        # Physical constants
        self.M = M
        self.R = R
        self.ee = ee
        self.mu_s = mu_s
        self.mu_w = mu_w

        # Work and step counter
        self.P = 0.0
        self.WzI = 0.0
        self.i = 0
        self.N = 100

        # Centroid velocity components
        self.vx = 0.0
        self.vy = 0.0

        # Angular velocity components
        self.omega_x = 0.0
        self.omega_y = 0.0
        self.omega_z = 0.0

        # Slip speeds and angles at cushion (I) and table (C)
        self.slip_speed = 0.0
        self.slip_angle = 0.0
        self.slip_speed_prime = 0.0
        self.slip_angle_prime = 0.0

    def _update_slip_speeds_and_angles(self):
        """
        Update the slip speeds and angles at the cushion (I) and table (C).
        """
        R = self.R

        # Velocities at the cushion (I)
        v_xI = self.vx + self.omega_y * R * sin_theta - self.omega_z * R * cos_theta
        v_yI = -self.vy * sin_theta + self.omega_x * R

        # Velocities at the table (C)
        v_xC = self.vx - self.omega_y * R
        v_yC = self.vy + self.omega_x * R

        # Update slip speed and angle at the cushion (I)
        self.slip_speed = math.sqrt(v_xI**2 + v_yI**2)
        self.slip_angle = math.atan2(v_yI, v_xI)
        if self.slip_angle < 0:
            self.slip_angle += 2 * math.pi

        # Update slip speed and angle at the table (C)
        self.slip_speed_prime = math.sqrt(v_xC**2 + v_yC**2)
        self.slip_angle_prime = math.atan2(v_yC, v_xC)
        if self.slip_angle_prime < 0:
            self.slip_angle_prime += 2 * math.pi

    def _update_velocity(self, delta_P):
        """
        Update the centroid velocity components.
        """
        mu_s = self.mu_s
        mu_w = self.mu_w
        M = self.M

        # Update vx
        self.vx -= (
            (1 / M)
            * (
                mu_w * math.cos(self.slip_angle)
                + mu_s
                * math.cos(self.slip_angle_prime)
                * (sin_theta + mu_w * math.sin(self.slip_angle) * cos_theta)
            )
            * delta_P
        )

        # Update vy
        self.vy -= (
            (1 / M)
            * (
                cos_theta
                - mu_w * sin_theta * math.sin(self.slip_angle)
                + mu_s
                * math.sin(self.slip_angle_prime)
                * (sin_theta + mu_w * math.sin(self.slip_angle) * cos_theta)
            )
            * delta_P
        )

    def _update_angular_velocity(self, delta_P):
        """
        Update the angular velocity components.
        """
        mu_s = self.mu_s
        mu_w = self.mu_w
        M = self.M
        R = self.R
        factor = 5 / (2 * M * R)

        self.omega_x += (
            -factor
            * (
                mu_w * math.sin(self.slip_angle)
                + mu_s
                * math.sin(self.slip_angle_prime)
                * (sin_theta + mu_w * math.sin(self.slip_angle) * cos_theta)
            )
            * delta_P
        )

        self.omega_y += (
            -factor
            * (
                mu_w * math.cos(self.slip_angle) * sin_theta
                - mu_s
                * math.cos(self.slip_angle_prime)
                * (sin_theta + mu_w * math.sin(self.slip_angle) * cos_theta)
            )
            * delta_P
        )

        self.omega_z += (
            factor * (mu_w * math.cos(self.slip_angle) * cos_theta) * delta_P
        )

    def _update_work_done(self, delta_P):
        """
        Update the work done.
        """
        delta_WzI = delta_P * abs(self.vy)
        self.WzI += delta_WzI
        self.P += delta_P

    def _update_single_step(self, delta_P):
        """
        Perform a single update step for the simulation.
        """
        self._update_slip_speeds_and_angles()
        self._update_velocity(delta_P)
        self._update_angular_velocity(delta_P)
        self._update_work_done(delta_P)

        self.i += 1
        if self.i > 10 * self.N:
            raise Exception("Solution not found")

    def compression_phase(self):
        """
        Run the compression phase until the y-velocity is no longer positive.
        """
        delta_P = max((self.M * self.vy) / self.N, 0.001)
        while self.vy > 0:
            self._update_single_step(delta_P)

    def restitution_phase(self, target_work_rebound):
        """
        Run the restitution phase until the work at the cushion (WzI) reaches the target rebound work.
        """
        delta_P = max(target_work_rebound / self.N, 0.001)
        self.WzI = 0
        while self.WzI < target_work_rebound:
            self._update_single_step(delta_P)

    def solve_paper(self, v0, alpha, omega0S, omega0T):
        """
        Convenience method that initializes the simulation parameters using polar components.
        """
        self.solve(
            v0 * math.cos(alpha),
            v0 * math.sin(alpha),
            -omega0T * math.sin(alpha),
            omega0T * math.cos(alpha),
            omega0S,
        )

    def solve(self, vx, vy, omega_x, omega_y, omega_z):
        """
        Initialize the state and run both the compression and restitution phases.
        """
        self.vx = vx
        self.vy = vy
        self.omega_x = omega_x
        self.omega_y = omega_y
        self.omega_z = omega_z

        self.WzI = 0
        self.P = 0
        self.i = 0

        self.compression_phase()
        target_work_rebound = self.ee**2 * self.WzI
        self.restitution_phase(target_work_rebound)


def _solve_mathaven(ball: Ball, cushion: Cushion) -> Tuple[Ball, Cushion]:
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
    sim = Mathavan(M, R, ee, ball.params.u_s, mu)
    sim.solve(vx_rot, vy_rot, omega_x_rot, omega_y_rot, omega_z_rot)

    # Update the rotated state with the simulation's output.
    rvw_R[1, 0] = sim.vx
    rvw_R[1, 1] = sim.vy
    rvw_R[2, 0] = sim.omega_x
    rvw_R[2, 1] = sim.omega_y
    rvw_R[2, 2] = sim.omega_z

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
        return _solve_mathaven(ball, cushion)


@attrs.define
class Mathavan2010Circular(CoreBallCCushionCollision):
    model: BallCCushionModel = attrs.field(
        default=BallCCushionModel.MATHAVAN_2010, init=False, repr=False
    )

    def solve(
        self, ball: Ball, cushion: CircularCushionSegment
    ) -> Tuple[Ball, CircularCushionSegment]:
        return _solve_mathaven(ball, cushion)


# Test script for debugging purposes.
if __name__ == "__main__":
    # For this test, assume PocketTableSpecs and BallParams are available
    # and provide the appropriate cushion height and ball parameters.
    from pooltool.objects.ball.datatypes import BallParams
    from pooltool.objects.table.specs import PocketTableSpecs

    h = PocketTableSpecs().cushion_height

    cushion = LinearCushionSegment(
        "cushion",
        p1=np.array([0, -1, h], dtype=np.float64),
        p2=np.array([0, +1, h], dtype=np.float64),
    )

    R = BallParams.default().R
    pos = [-R, 0, R]

    # Ball hitting the left-side cushion.
    ball = Ball("cue")
    ball.state.rvw[0] = pos
    # Note: the ball's translational velocity is set to (1, 0, 0) in the table frame.
    # Given that cushion.get_normal will likely return (1,0,0) for a left cushion,
    # the coordinate transform rotates the state so that (1,0) becomes (0,1) in the cushion frame.
    ball.state.rvw[1] = (1, 0, 0)
    ball.state.s = 2

    print("Before collision:")
    print(ball.state.rvw)
    mathavan = Mathavan2010Linear()
    ball_after, _ = mathavan.resolve(ball, cushion, inplace=False)
    print("After collision (original state unchanged):")
    print(ball.state.rvw)
    print("After collision (returned state):")
    print(ball_after.state.rvw)
