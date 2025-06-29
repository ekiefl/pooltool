import math
from typing import TypeVar

import attrs
import numpy as np
from numba import jit

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

Cushion = TypeVar("Cushion", LinearCushionSegment, CircularCushionSegment)


@jit(nopython=True, cache=const.use_numba_cache)
def get_sin_and_cos_theta(h: float, R: float) -> tuple[float, float]:
    """Returns sin(theta), cos(theta)"""
    sin_theta = (h - R) / R
    cos_theta = np.sqrt(1 - sin_theta**2)
    return sin_theta, cos_theta


@jit(nopython=True, cache=const.use_numba_cache)
def calculate_slip_speeds_and_angles(
    R: float,
    sin_theta: float,
    cos_theta: float,
    vx: float,
    vy: float,
    omega_x: float,
    omega_y: float,
    omega_z: float,
) -> tuple[float, float, float, float]:
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

    return slip_speed, slip_angle, slip_speed_prime, slip_angle_prime


@jit(nopython=True, cache=const.use_numba_cache)
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
    delta_p: float,
) -> tuple[float, float]:
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
        * delta_p
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
        * delta_p
    )

    return vx_new, vy_new


@jit(nopython=True, cache=const.use_numba_cache)
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
    delta_p: float,
) -> tuple[float, float, float]:
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
        * delta_p
    )

    omega_y_new = omega_y + (
        -factor
        * (
            mu_w * math.cos(slip_angle) * sin_theta
            - mu_s
            * math.cos(slip_angle_prime)
            * (sin_theta + mu_w * math.sin(slip_angle) * cos_theta)
        )
        * delta_p
    )

    omega_z_new = omega_z + (
        factor * (mu_w * math.cos(slip_angle) * cos_theta) * delta_p
    )

    return omega_x_new, omega_y_new, omega_z_new


@jit(nopython=True, cache=const.use_numba_cache)
def calculate_work_done(vy: float, cos_theta: float, delta_p: float) -> float:
    """
    Calculate the work done for a single step.
    """
    return delta_p * abs(vy) * cos_theta


@jit(nopython=True, cache=const.use_numba_cache)
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
    delta_p: float = 0.0001,
) -> tuple[float, float, float, float, float, float]:
    """Run the compression phase until the y-velocity is no longer positive.

    Args:
        M: Mass of the ball
        R: Radius of the ball
        mu_s: Sliding friction coefficient between ball and table
        mu_w: Sliding friction coefficient between ball and cushion
        sin_theta: Sine of contact angle
        cos_theta: Cosine of contact angle
        vx: Initial x-velocity
        vy: Initial y-velocity
        omega_x: Initial x-angular velocity
        omega_y: Initial y-angular velocity
        omega_z: Initial z-angular velocity
        max_steps: Maximum number of steps for numerical integration
        delta_p: Impulse step size

    Returns:
        Tuple of (vx, vy, omega_x, omega_y, omega_z, total_work)
    """
    WzI = 0.0
    step_count = 0

    # Calculate initial step size based on initial velocity
    delta_p = max((M * vy) / max_steps, delta_p)

    while vy > 0:
        # Calculate slip states
        _, slip_angle, _, slip_angle_prime = calculate_slip_speeds_and_angles(
            R,
            sin_theta,
            cos_theta,
            vx,
            vy,
            omega_x,
            omega_y,
            omega_z,
        )

        # Update velocities
        vx_next, vy_next = update_velocity(
            M,
            mu_s,
            mu_w,
            sin_theta,
            cos_theta,
            vx,
            vy,
            slip_angle,
            slip_angle_prime,
            delta_p,
        )

        if vy > 0 and vy_next <= 0:
            # Threshold has crossed.
            vx_refine, vy_refine = vx, vy
            omega_x_refine, omega_y_refine, omega_z_refine = omega_x, omega_y, omega_z
            WzI_refine = WzI

            # Use binary search to find the precise crossing point
            refine_delta_p = delta_p
            for _ in range(8):
                refine_delta_p /= 2

                _, slip_angle_refine, _, slip_angle_prime_refine = (
                    calculate_slip_speeds_and_angles(
                        R,
                        sin_theta,
                        cos_theta,
                        vx_refine,
                        vy_refine,
                        omega_x_refine,
                        omega_y_refine,
                        omega_z_refine,
                    )
                )

                vx_test, vy_test = update_velocity(
                    M,
                    mu_s,
                    mu_w,
                    sin_theta,
                    cos_theta,
                    vx_refine,
                    vy_refine,
                    slip_angle_refine,
                    slip_angle_prime_refine,
                    refine_delta_p,
                )

                if vy_test <= 0:
                    # This step is too large.
                    continue

                # This step doesn't cross threshold, so we can safely update the state.
                vx_refine, vy_refine = vx_test, vy_test

                omega_x_refine, omega_y_refine, omega_z_refine = (
                    update_angular_velocity(
                        M,
                        R,
                        mu_s,
                        mu_w,
                        sin_theta,
                        cos_theta,
                        omega_x_refine,
                        omega_y_refine,
                        omega_z_refine,
                        slip_angle_refine,
                        slip_angle_prime_refine,
                        refine_delta_p,
                    )
                )

                delta_WzI = calculate_work_done(vy_refine, cos_theta, refine_delta_p)
                WzI_refine += delta_WzI

            # Return the refined state that's as close as possible to threshold
            return (
                vx_refine,
                vy_refine,
                omega_x_refine,
                omega_y_refine,
                omega_z_refine,
                WzI_refine,
            )

        # Continue with normal update if no refinement needed.
        vx, vy = vx_next, vy_next
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
            slip_angle,
            slip_angle_prime,
            delta_p,
        )

        # Calculate work for this step
        delta_WzI = calculate_work_done(vy, cos_theta, delta_p)
        WzI += delta_WzI

        # Update step count
        step_count += 1
        if step_count > 10 * max_steps:
            raise RuntimeError("Solution not found in compression phase")

    return vx, vy, omega_x, omega_y, omega_z, WzI


@jit(nopython=True, cache=const.use_numba_cache)
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
    delta_p: float = 0.0001,
) -> tuple[float, float, float, float, float]:
    """
    Run the restitution phase until the work at the cushion (WzI) reaches the target rebound work.
    """
    WzI = 0.0
    step_count = 0

    delta_p = max(target_work_rebound / max_steps, delta_p)

    while WzI < target_work_rebound:
        _, slip_angle, _, slip_angle_prime = calculate_slip_speeds_and_angles(
            R, sin_theta, cos_theta, vx, vy, omega_x, omega_y, omega_z
        )

        next_delta_WzI = calculate_work_done(vy, cos_theta, delta_p)

        if WzI + next_delta_WzI > target_work_rebound:
            # The next step would pass the threshold, so we refine the step size.
            remaining_work = target_work_rebound - WzI

            # Start a binary search.
            refine_vx, refine_vy = vx, vy
            refine_omega_x, refine_omega_y, refine_omega_z = omega_x, omega_y, omega_z
            refine_WzI = WzI

            # Calculate a smaller delta_p that should be just right.
            refine_delta_p = remaining_work / (abs(vy) * cos_theta)

            # Apply this refined step
            _, slip_angle_refine, _, slip_angle_prime_refine = (
                calculate_slip_speeds_and_angles(
                    R,
                    sin_theta,
                    cos_theta,
                    refine_vx,
                    refine_vy,
                    refine_omega_x,
                    refine_omega_y,
                    refine_omega_z,
                )
            )

            refine_vx, refine_vy = update_velocity(
                M,
                mu_s,
                mu_w,
                sin_theta,
                cos_theta,
                refine_vx,
                refine_vy,
                slip_angle_refine,
                slip_angle_prime_refine,
                refine_delta_p,
            )

            refine_omega_x, refine_omega_y, refine_omega_z = update_angular_velocity(
                M,
                R,
                mu_s,
                mu_w,
                sin_theta,
                cos_theta,
                refine_omega_x,
                refine_omega_y,
                refine_omega_z,
                slip_angle_refine,
                slip_angle_prime_refine,
                refine_delta_p,
            )

            # Calculate actual work done
            actual_work = calculate_work_done(refine_vy, cos_theta, refine_delta_p)
            refine_WzI += actual_work

            return (
                refine_vx,
                refine_vy,
                refine_omega_x,
                refine_omega_y,
                refine_omega_z,
            )

        # Continue with normal update if no refinement needed or if refinement failed
        vx, vy = update_velocity(
            M,
            mu_s,
            mu_w,
            sin_theta,
            cos_theta,
            vx,
            vy,
            slip_angle,
            slip_angle_prime,
            delta_p,
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
            slip_angle,
            slip_angle_prime,
            delta_p,
        )

        # Calculate work for this step
        delta_WzI = calculate_work_done(vy, cos_theta, delta_p)
        WzI += delta_WzI

        # Update step count
        step_count += 1
        if step_count > 10 * max_steps:
            raise RuntimeError("Solution not found in restitution phase")

    return vx, vy, omega_x, omega_y, omega_z


@jit(nopython=True, cache=const.use_numba_cache)
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
    max_steps: int = 5000,
    delta_p: float = 0.0001,
) -> tuple[float, float, float, float, float]:
    """Initialize the state and run both the compression and restitution phases.

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
        max_steps: Maximum number of steps for numerical integration
        delta_p: Impulse step size

    Returns:
        Tuple of (vx, vy, omega_x, omega_y, omega_z) after collision
    """
    sin_theta, cos_theta = get_sin_and_cos_theta(h, R)

    # Run the compression phase
    vx, vy, omega_x, omega_y, omega_z, WzI = compression_phase(
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
        max_steps,
        delta_p,
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
        max_steps,
        delta_p,
    )

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
    max_steps: int = 5000,
    delta_p: float = 0.0001,
) -> tuple[float, float, float, float, float]:
    """
    Convenience method that solves using parameters described in the paper.

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
        max_steps: Maximum number of steps for numerical integration
        delta_p: Impulse step size

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
        max_steps,
        delta_p,
    )


def solve_mathavan(
    ball: Ball, cushion: Cushion, max_steps: int = 5000, delta_p: float = 0.0001
) -> tuple[Ball, Cushion]:
    """
    Run the Mathavan model to simulate the ball-cushion collision.

    This version rotates the ball state into the cushion frame using the same coordinate
    transformation functions as Han2005. However, because the Mathavan simulation expects
    the collision approach to be along the positive y-axis, we rotate the state so that the
    cushion's normal (obtained via cushion.get_normal) maps to (0,1).

    Args:
        ball: The ball involved in the collision
        cushion: The cushion segment involved in the collision
        max_steps: Maximum number of steps for numerical integration
        delta_p: Impulse step size
    """
    M = ball.params.m
    R = ball.params.R
    ee = ball.params.e_c
    mu = ball.params.f_c
    u_s = ball.params.u_s
    h = cushion.height

    rvw = ball.state.rvw

    # Ensure the normal is pointing in the same direction as the ball's velocity.
    normal = cushion.get_normal(rvw)
    if np.dot(normal, rvw[1]) <= 0:
        normal = -normal

    # Rotate the ball's state into the cushion frame.
    psi = ptmath.angle(normal)
    angle_to_rotate = (math.pi / 2) - psi
    rvw_R = ptmath.coordinate_rotation(rvw.T, angle_to_rotate).T

    vx_rot = rvw_R[1, 0]
    vy_rot = rvw_R[1, 1]
    omega_x_rot = rvw_R[2, 0]
    omega_y_rot = rvw_R[2, 1]
    omega_z_rot = rvw_R[2, 2]

    vx_final, vy_final, omega_x_final, omega_y_final, omega_z_final = solve(
        M,
        R,
        h,
        ee,
        u_s,
        mu,
        vx_rot,
        vy_rot,
        omega_x_rot,
        omega_y_rot,
        omega_z_rot,
        max_steps,
        delta_p,
    )

    rvw_R[1, 0] = vx_final
    rvw_R[1, 1] = vy_final
    rvw_R[2, 0] = omega_x_final
    rvw_R[2, 1] = omega_y_final
    rvw_R[2, 2] = omega_z_final

    rvw_final = ptmath.coordinate_rotation(rvw_R.T, -angle_to_rotate).T

    ball.state = BallState(rvw_final, const.sliding)
    return ball, cushion


@attrs.define
class Mathavan2010Linear(CoreBallLCushionCollision):
    """Ball-cushion collision resolver for the Mathavan et al. (2010) collision model.

    This work predicts ball bounce angles and bounce speeds for the ball’s collisions
    with a cushion, under the assumption of insignificant cushion deformation.
    Differential equations are derived for the ball dynamics during the impact and these
    these equations are solved numerically.

    References:
        Mathavan S, Jackson MR, Parkin RM. A theoretical analysis of billiard
        ball-cushion dynamics under cushion impacts. Proceedings of the Institution of
        Mechanical Engineers, Part C. 2010;224(9):1863-1873.
        doi:10.1243/09544062JMES1964

        Available at
        https://drdavepoolinfo.com//physics_articles/Mathavan_IMechE_2010.pdf
    """

    max_steps: int = attrs.field(default=1000)
    delta_p: float = attrs.field(default=0.001)
    model: BallLCushionModel = attrs.field(
        default=BallLCushionModel.MATHAVAN_2010, init=False, repr=False
    )

    def solve(
        self, ball: Ball, cushion: LinearCushionSegment
    ) -> tuple[Ball, LinearCushionSegment]:
        """Resolve ball-cushion collision via Mathavan et al. (2010).

        This method computes the post-collision linear and angular velocities of a ball
        colliding with a cushion, taking into account both ball spin and frictional
        effects. The collision model is based on the theoretical analysis described by
        Mathavan et al., which considers 3D impact dynamics and the effects of topspin
        and sidespin on the rebound trajectory.

        The function analyzes the ball's incident velocity and spin components relative
        to the cushion's normal and tangential planes. It then applies the derived
        differential equations to calculate the collision dynamics through numerical
        integration, accounting for both the compression and restitution phases of
        impact. The model incorporates the sliding coefficient of friction between ball
        and cushion as well as between ball and table, along with the coefficient of
        restitution. Once the complete impulse exchange is calculated, the updated
        linear and angular velocities are determined and returned.

        The model assumes insignificant cushion deformation, which is reported to be
        valid for normal velocities up to 2.5 m/s, and accounts for transitions between
        sliding and rolling states during collision.
        """
        return solve_mathavan(ball, cushion, self.max_steps, self.delta_p)


@attrs.define
class Mathavan2010Circular(CoreBallCCushionCollision):
    """Ball-cushion collision resolver for the Mathavan et al. (2010) collision model.

    This work predicts ball bounce angles and bounce speeds for the ball’s collisions
    with a cushion, under the assumption of insignificant cushion deformation.
    Differential equations are derived for the ball dynamics during the impact and these
    these equations are solved numerically.

    References:
        Mathavan S, Jackson MR, Parkin RM. A theoretical analysis of billiard
        ball-cushion dynamics under cushion impacts. Proceedings of the Institution of
        Mechanical Engineers, Part C. 2010;224(9):1863-1873.
        doi:10.1243/09544062JMES1964

        Available at
        https://drdavepoolinfo.com//physics_articles/Mathavan_IMechE_2010.pdf
    """

    max_steps: int = attrs.field(default=1000)
    delta_p: float = attrs.field(default=0.001)
    model: BallCCushionModel = attrs.field(
        default=BallCCushionModel.MATHAVAN_2010, init=False, repr=False
    )

    def solve(
        self, ball: Ball, cushion: CircularCushionSegment
    ) -> tuple[Ball, CircularCushionSegment]:
        """Resolve ball-cushion collision via Mathavan et al. (2010).

        This method computes the post-collision linear and angular velocities of a ball
        colliding with a cushion, taking into account both ball spin and frictional
        effects. The collision model is based on the theoretical analysis described by
        Mathavan et al., which considers 3D impact dynamics and the effects of topspin
        and sidespin on the rebound trajectory.

        The function analyzes the ball's incident velocity and spin components relative
        to the cushion's normal and tangential planes. It then applies the derived
        differential equations to calculate the collision dynamics through numerical
        integration, accounting for both the compression and restitution phases of
        impact. The model incorporates the sliding coefficient of friction between ball
        and cushion as well as between ball and table, along with the coefficient of
        restitution. Once the complete impulse exchange is calculated, the updated
        linear and angular velocities are determined and returned.

        The model assumes insignificant cushion deformation, which is reported to be
        valid for normal velocities up to 2.5 m/s, and accounts for transitions between
        sliding and rolling states during collision.
        """
        return solve_mathavan(ball, cushion, self.max_steps, self.delta_p)
