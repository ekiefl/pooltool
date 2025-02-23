import math
from typing import Tuple, TypeVar

import attrs

import pooltool.constants as const
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

# Fixed values for cushion contact point angles
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
        self.N = 5000

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

    This function extracts the necessary parameters and initial conditions
    from the ball object, creates a Mathavan simulation instance, runs the collision,
    and then updates the ball state accordingly.
    """
    # Map pooltool ball parameters to Mathavan parameters.
    # Adjust these mappings if your pooltool parameter names differ.
    M = ball.params.m
    R = ball.params.R
    ee = ball.params.e_c  # using cushion restitution coefficient
    # For simplicity, we assume the same friction coefficient for both modes.
    mu = ball.params.f_c

    # Extract the initial condition from ball.state.rvw.
    # We assume ball.state.rvw is a NumPy array where:
    # - row 1 contains the translational velocity [vx, vy, ...]
    # - row 2 contains the rotational velocity [omega_x, omega_y, omega_z]
    vx = ball.state.rvw[1, 0]
    vy = ball.state.rvw[1, 1]
    omega_x = ball.state.rvw[2, 0]
    omega_y = ball.state.rvw[2, 1]
    omega_z = ball.state.rvw[2, 2]

    # Create and run the Mathavan simulation.
    sim = Mathavan(M, R, ee, mu, mu)
    # Here you can choose to use solve_paper (if incident angle formulation is desired)
    # or solve directly with the state variables.
    sim.solve(vx, vy, omega_x, omega_y, omega_z)

    # Update the ball's state with the simulation results.
    new_rvw = ball.state.rvw.copy()
    new_rvw[1, 0] = sim.vx
    new_rvw[1, 1] = sim.vy
    new_rvw[2, 0] = sim.omega_x
    new_rvw[2, 1] = sim.omega_y
    new_rvw[2, 2] = sim.omega_z

    ball.state = BallState(new_rvw, const.sliding)
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
