from abc import ABC, abstractmethod
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball
from pooltool.physics.dimensionality import Dim


# stolen from stick_ball/core.py
# TODO: move to common place
def final_ball_motion_state(rvw: NDArray[np.float64], R: float) -> int:
    """Return the final (post-strike) motion state label.

    If the z-velocity is non-zero the ball is considered airborne, otherwise
    it is sliding (a struck ball is always kinetic).

    Notes:
        - A universal ``final_ball_motion_state`` fn could be a good idea.
    """
    if rvw[1, 2] != 0.0:
        return const.airborne

    return const.sliding


class _BaseStrategy(Protocol):
    def make_kiss(self, ball1: Ball, ball2: Ball) -> tuple[Ball, Ball]: ...

    def resolve(
        self, ball1: Ball, ball2: Ball, inplace: bool = False
    ) -> tuple[Ball, Ball]: ...


class BallBallCollisionStrategy(_BaseStrategy, Protocol):
    """Ball-ball collision models must satisfy this protocol"""

    dim: Dim

    def solve(self, ball1: Ball, ball2: Ball) -> tuple[Ball, Ball]:
        """This method resolves a ball-ball collision"""
        ...


class CoreBallBallCollision(ABC):
    """Operations used by every ball-ball collision resolver"""

    def make_kiss(self, ball1: Ball, ball2: Ball) -> tuple[Ball, Ball]:
        """Position balls at precise target separation before collision resolution.

        This method adjusts ball positions so their centers are separated by exactly
        ``R1 + R2 + spacer``, where ``spacer`` is a small epsilon to prevent ball
        intersection that occurs due to floating-point precision if an explicit spacer
        is not added, and then enforces each ball's table constraint without disturbing
        that separation.

        The primary method solves a quadratic equation for the time offset t at which
        the balls, each moving along its own straight-line trajectory
        ``r + t * v``, are at the target separation. The smallest-magnitude real root
        is chosen. Acceleration terms are assumed negligible.

        If both balls are non-translating, if the quadratic has no real root (e.g. a
        grazing trajectory), or if the midpoint (collision point) shifts by more than
        5x the spacer (which can occur if balls are moving with nearly the same
        velocity), a fallback strategy is used that moves the balls uniformly along the
        line of centers until they're separated by the target distance.

        The time offset may be negative (overlapping balls are rewound) or positive
        (separated balls are advanced); the smallest-magnitude root is taken either way.

        Either strategy can leave a ball at a physically wrong height: the fallback
        moves both balls along a tilted line of centers when one is airborne, and the
        primary method can carry an airborne ball through the table, e.g. rewinding a
        just-launched ball backward along its upward velocity or advancing a landing
        ball forward along its downward one. Such balls are lifted by sliding them
        along the sphere of radius ``R1 + R2 + spacer`` centered on the other ball, so
        the separation is preserved exactly. See :func:`_constrain_to_table`.

        Returns:
            tuple[Ball, Ball]:
                ``ball1`` and ``ball2`` modified in place with adjusted positions.
        """
        r1 = ball1.state.rvw[0]
        r2 = ball2.state.rvw[0]
        v1 = ball1.state.rvw[1]
        v2 = ball2.state.rvw[1]

        spacer = const.MIN_DIST
        target = ball1.params.R + ball2.params.R + spacer

        both_nontranslating = (
            ball1.state.s in const.nontranslating
            and ball2.state.s in const.nontranslating
        )
        use_velocity, r1_corrected, r2_corrected = (
            (False, r1, r2)
            if both_nontranslating
            else _velocity_positions(r1, r2, v1, v2, target, spacer)
        )

        if not use_velocity:
            r1_corrected, r2_corrected = _fallback_positions(r1, r2, target)

        r1_corrected, r2_corrected = _constrain_to_table(
            ball1, ball2, r1_corrected, r2_corrected, target, use_velocity
        )

        ball1.state.rvw[0] = r1_corrected
        ball2.state.rvw[0] = r2_corrected

        return ball1, ball2

    def resolve_continually_touching(
        self, ball1: Ball, ball2: Ball
    ) -> tuple[Ball, Ball]:
        """Prevent repeated collision detection for nearly-touching balls moving in unison.

        This method is called to handle rare cases where balls are moving with very
        similar velocities. This can happen in some edge cases when frozen balls in a
        perfect line are given energy along their line, (e.g. Newton's cradle). Without
        intervention, the balls repeatedly trigger events microseconds apart that stall
        progression of the simulation, sometimes indefinitely, via an explosion of
        events.

        This is an unfortunate consequence of modeling non-instantaneous multibody
        collisions using instantaneous pairwise collisions, and resolving it requires
        some phenomonelogical intervention that hopefully appears to be realistic,
        despite it not being grounded in theory.

        The solution is applied in this method, and uses a momentum transfer mechanism:
        the "chased" ball (slower in the line-of-centers direction) steals a fraction of
        the "chaser's" radial momentum. This creates gradual separation over time,
        preventing the balls from triggering repeated collision events while maintaining
        physically plausible behavior.

        Algorithm:
            1. Projects velocities onto line of centers to get radial components
            2. If radial relative velocity is below threshold (< 1mm/s):
               - Identifies which ball is "chasing" (higher radial velocity)
               - Chased ball steals 10% of chaser's radial momentum
               - Chaser loses this momentum, chased gains it
            3. Tangential velocity components remain unchanged

        Args:
            ball1: First ball in the collision
            ball2: Second ball in the collision

        Returns:
            Modified ball1 and ball2 with adjusted velocities

        Notes:
            - Practically speaking, this is a no-op method for all but the most
              contrived simulation conditions. For one such condition, see
              `sandbox/newtons_cradle.py`
        """
        r1 = ball1.state.rvw[0]
        r2 = ball2.state.rvw[0]
        v1 = ball1.state.rvw[1]
        v2 = ball2.state.rvw[1]

        v1_speed = ptmath.norm3d(v1)
        v2_speed = ptmath.norm3d(v2)
        both_moving = v1_speed > 0 and v2_speed > 0

        if not both_moving:
            return ball1, ball2

        theft_fraction = 0.10
        velocity_similarity_threshold = 0.9

        line_of_centers = ptmath.unit_vector(r2 - r1)

        # Velocities projected onto the line of centers (loc).
        v1_loc = np.dot(v1, line_of_centers)
        v2_loc = np.dot(v2, line_of_centers)

        cosine_similarity = np.dot(v1, v2) / (v1_speed * v2_speed)
        velocities_aligned = cosine_similarity > velocity_similarity_threshold

        if abs(v2_loc - v1_loc) < 0.01 and velocities_aligned:
            if v1_loc > v2_loc:
                chaser_loc_vel = v1_loc
                ball1_is_chaser = True
            else:
                chaser_loc_vel = v2_loc
                ball1_is_chaser = False

            # Chased ball steals fraction of chaser's line of centers momentum
            # FIXME: We assume equal mass, so transfer velocity directly
            stolen_loc_velocity = chaser_loc_vel * theft_fraction

            if ball1_is_chaser:
                v1_loc_new = v1_loc - stolen_loc_velocity
                v2_loc_new = v2_loc + stolen_loc_velocity
            else:
                v1_loc_new = v1_loc + stolen_loc_velocity
                v2_loc_new = v2_loc - stolen_loc_velocity

            v1_corrected = v1 - v1_loc * line_of_centers + v1_loc_new * line_of_centers
            v2_corrected = v2 - v2_loc * line_of_centers + v2_loc_new * line_of_centers

            momentum_before = v1 + v2
            momentum_after = v1_corrected + v2_corrected
            assert np.allclose(momentum_before, momentum_after, rtol=1e-10)

            ball1.state.rvw[1] = v1_corrected
            ball2.state.rvw[1] = v2_corrected

        return ball1, ball2

    def resolve(
        self, ball1: Ball, ball2: Ball, inplace: bool = False
    ) -> tuple[Ball, Ball]:
        if not inplace:
            ball1 = ball1.copy()
            ball2 = ball2.copy()

        ball1, ball2 = self.make_kiss(ball1, ball2)
        ball1, ball2 = self.solve(ball1, ball2)
        ball1, ball2 = self.resolve_continually_touching(ball1, ball2)

        return ball1, ball2

    @abstractmethod
    def solve(self, ball1: Ball, ball2: Ball) -> tuple[Ball, Ball]:
        pass


Z_HAT = np.array([0.0, 0.0, 1.0])
X_HAT = np.array([1.0, 0.0, 0.0])
XY_MASK = np.array([1.0, 1.0, 0.0])


def _velocity_positions(
    r1: NDArray[np.float64],
    r2: NDArray[np.float64],
    v1: NDArray[np.float64],
    v2: NDArray[np.float64],
    target: float,
    spacer: float,
) -> tuple[bool, NDArray[np.float64], NDArray[np.float64]]:
    """Move both balls along their own velocities to the target separation.

    Solves ``|(r2 + t v2) - (r1 + t v1)| == target`` for the smallest-magnitude real
    time offset t, which is negative for overlapping balls and positive for separated
    ones, and returns the shifted positions.

    Returns:
        tuple[bool, NDArray[np.float64], NDArray[np.float64]]:
            Whether the correction is usable, followed by the corrected positions. The
            correction is unusable, and the original positions are returned, when the
            quadratic has no real root (e.g. a grazing trajectory) or when the midpoint
            shifts by more than 5x the spacer (balls moving with nearly the same
            velocity).
    """
    B = v2 - v1
    C = r2 - r1
    alpha = np.dot(B, B)
    beta = 2 * np.dot(B, C)
    gamma = np.dot(C, C) - target**2
    roots_complex = ptmath.roots.quadratic.solve(alpha, beta, gamma)
    t = ptmath.roots.get_real_smallest_magnitude_root(roots_complex)

    if not np.isfinite(t):
        return False, r1, r2

    r1_corrected = r1 + t * v1
    r2_corrected = r2 + t * v2

    midpoint_shift = ptmath.norm3d((r1_corrected + r2_corrected - r1 - r2) / 2)
    if midpoint_shift > 5 * spacer:
        return False, r1, r2

    return True, r1_corrected, r2_corrected


def _fallback_positions(
    r1: NDArray[np.float64], r2: NDArray[np.float64], target: float
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Move both balls uniformly along the line of centers to the target separation.

    Used when the balls are nontranslating (no velocity to trace back along), when the
    velocity-based correction has no real root, or when it would shift the collision
    point excessively.
    """
    direction = ptmath.unit_vector(r2 - r1)
    correction = target - ptmath.norm3d(r2 - r1)
    return r1 - correction / 2 * direction, r2 + correction / 2 * direction


def _violates_table(ball: Ball, z: float) -> bool:
    """Whether a ball at height ``z`` breaks its table constraint.

    Non-airborne balls must rest exactly on the table (``z == R``); both lift and
    penetration are violations. Airborne balls must only stay above it (``z >= R``).
    """
    if ball.state.s == const.airborne:
        return z < ball.params.R

    return z != ball.params.R


def _constrain_to_table(
    ball1: Ball,
    ball2: Ball,
    r1: NDArray[np.float64],
    r2: NDArray[np.float64],
    target: float,
    use_velocity: bool,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Lift any ball that violates its table constraint, preserving the separation.

    Each violating ball is slid along the sphere of radius ``target`` centered on the
    other ball's current position until its center is at height ``R``, so the
    separation set by :meth:`CoreBallBallCollision.make_kiss` survives intact. The
    deeper ball is lifted first, about the other ball's uncorrected position; the second
    lift then pivots on the first ball's corrected position. Each lift moves only one
    ball, so the second cannot undo the first.

    A resting ball displaced by the fallback is the exception. Only the fallback can
    move a resting ball vertically, and it does so along a line of centers that is
    nearly vertical whenever the displacement is appreciable. Sliding the resting ball
    back along the sphere would then trade a sub-micron height error for a horizontal
    move of order ``sqrt(2 * target * dz)``, hundreds of times larger, teleporting a
    ball that never moved. Instead the resting ball returns straight to the table and
    the airborne ball, which is free to move, absorbs the correction; see
    :func:`_lift_vertically`.

    Args:
        use_velocity:
            If True, each ball is lifted within the vertical plane of its own velocity
            (the plane its flight actually occupied), which is the right choice after
            the velocity-based correction. If False, as after the fallback, the vertical
            plane through both centers is used instead.
    """
    balls = (ball1, ball2)
    positions = [r1, r2]

    for i in sorted((0, 1), key=lambda i: positions[i][2]):
        if not _violates_table(balls[i], positions[i][2]):
            continue

        mover, pivot = positions[i], positions[1 - i]
        R = balls[i].params.R

        if not use_velocity and balls[i].state.s != const.airborne:
            positions[i], positions[1 - i] = _lift_vertically(mover, pivot, target, R)
            continue

        velocity = balls[i].state.rvw[1] if use_velocity else np.zeros(3)
        positions[i] = _lift_to_height(mover, pivot, target, R, velocity)

    return positions[0], positions[1]


def _lift_vertically(
    mover: NDArray[np.float64],
    pivot: NDArray[np.float64],
    d: float,
    R: float,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Move ``mover`` straight to height ``R`` and re-space ``pivot`` along the line of centers.

    Used for a resting ball that the fallback pushed off the table. Its horizontal
    position is left untouched and only its height is restored. The other ball must be
    airborne (two resting balls share a horizontal line of centers and are never pushed
    vertically), so it is free to move: it is placed at distance ``d`` from the lifted
    mover along the original line of centers. This also covers the geometry where the
    pivot sits more than ``d`` above the table, which no slide along the sphere could
    solve.
    """
    lifted = mover * XY_MASK + R * Z_HAT
    return lifted, lifted + d * ptmath.unit_vector(pivot - lifted)


def _lift_to_height(
    mover: NDArray[np.float64],
    pivot: NDArray[np.float64],
    d: float,
    R: float,
    velocity: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Slide ``mover`` along the sphere of radius ``d`` around ``pivot`` until its height is ``R``.

    Every point at distance ``d`` from ``pivot`` lies on a sphere around it. Cutting
    that sphere with a vertical plane through ``mover`` gives a circle along which
    ``mover`` can slide without changing its distance to ``pivot``. The plane is the
    one containing ``velocity``, so the correction stays inside the ball's own plane
    of flight and introduces no sideways nudge. With no horizontal velocity, or if
    that plane's circle never reaches height ``R`` (its center sits at ``pivot``'s
    height, so this happens only when ``pivot`` is itself sunk deeper than the circle's
    radius, i.e. a near-grazing cut with both balls below the table), the vertical
    plane through both centers is used instead; it passes through ``pivot``, so its
    circle is a great circle that reaches ``R`` whenever ``pivot`` is within ``d`` of it.

    Of the two points on the circle at height ``R``, the one on ``mover``'s side of
    the circle's vertical center line is chosen. That point is simultaneously the
    nearest one, the smallest correction, and the one that never passes ``mover``
    through ``pivot``. If ``mover`` sits exactly on that center line, the positive
    side is chosen arbitrarily.
    """
    e1 = _centers_plane_axis(mover, pivot)

    horizontal_velocity = velocity * XY_MASK
    if ptmath.norm3d(horizontal_velocity) > 0:
        e1_velocity = ptmath.unit_vector(horizontal_velocity)
        if _circle_reaches_height(mover, pivot, d, R, e1_velocity):
            e1 = e1_velocity

    center, radius = _circle_on_sphere(mover, pivot, d, e1)
    a = (R - center[2]) / radius
    side = 1.0 if np.dot(mover - center, e1) >= 0 else -1.0
    b = side * np.sqrt(1.0 - a * a)

    return center + radius * (b * e1 + a * Z_HAT)


def _centers_plane_axis(
    mover: NDArray[np.float64], pivot: NDArray[np.float64]
) -> NDArray[np.float64]:
    """Horizontal unit vector from ``pivot`` toward ``mover``.

    When ``mover`` is directly above or below ``pivot`` there is no such direction,
    and the x-axis is chosen arbitrarily.
    """
    horizontal = (mover - pivot) * XY_MASK
    if ptmath.norm3d(horizontal) == 0:
        return X_HAT

    return ptmath.unit_vector(horizontal)


def _circle_on_sphere(
    mover: NDArray[np.float64],
    pivot: NDArray[np.float64],
    d: float,
    e1: NDArray[np.float64],
) -> tuple[NDArray[np.float64], float]:
    """Center and radius of the circle cut from the sphere by a vertical plane.

    The sphere has radius ``d`` around ``pivot``. The plane passes through ``mover``
    and is spanned by the horizontal unit vector ``e1`` and the vertical.
    """
    normal = ptmath.cross(e1, Z_HAT)
    offset = np.dot(mover - pivot, normal)
    center = pivot + offset * normal
    radius = np.sqrt(d * d - offset * offset)

    return center, radius


def _circle_reaches_height(
    mover: NDArray[np.float64],
    pivot: NDArray[np.float64],
    d: float,
    R: float,
    e1: NDArray[np.float64],
) -> bool:
    """Whether the circle cut by the vertical plane along ``e1`` reaches height ``R``."""
    center, radius = _circle_on_sphere(mover, pivot, d, e1)
    return abs(R - center[2]) <= radius
