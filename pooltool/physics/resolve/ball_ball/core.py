from abc import ABC, abstractmethod
from typing import Protocol

import numpy as np

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball


class _BaseStrategy(Protocol):
    def make_kiss(self, ball1: Ball, ball2: Ball) -> tuple[Ball, Ball]: ...

    def resolve(
        self, ball1: Ball, ball2: Ball, inplace: bool = False
    ) -> tuple[Ball, Ball]: ...


class BallBallCollisionStrategy(_BaseStrategy, Protocol):
    """Ball-ball collision models must satisfy this protocol"""

    def solve(self, ball1: Ball, ball2: Ball) -> tuple[Ball, Ball]:
        """This method resolves a ball-ball collision"""
        ...


class CoreBallBallCollision(ABC):
    """Operations used by every ball-ball collision resolver"""

    def _apply_fallback_positioning(
        self,
        ball1: Ball,
        ball2: Ball,
        r1: np.ndarray,
        r2: np.ndarray,
        spacer: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Apply fallback positioning by moving balls along line of centers.

        This fallback strategy moves balls uniformly along the line of centers until
        they're separated by the target distance (2*R + spacer).
        """
        correction = 2 * ball1.params.R - ptmath.norm3d(r2 - r1) + spacer
        r1_corrected = r1 - correction / 2 * ptmath.unit_vector(r2 - r1)
        r2_corrected = r2 + correction / 2 * ptmath.unit_vector(r2 - r1)
        return r1_corrected, r2_corrected

    def make_kiss(self, ball1: Ball, ball2: Ball) -> tuple[Ball, Ball]:
        """Position balls at precise target separation before collision resolution.

        This method adjusts ball positions so they are separated by exactly 2*R +
        spacer, where R is the ball radius and ``spacer`` is a small epsilon to prevent
        ball intersection that occurs due to floating-point precision if an explicit
        spacer is not added.

        The primary method solves a quadratic equation to find the time offset that
        positions the balls at the target separation. Balls are moved along their
        trajectories (position + velocity * time) to this configuration. Acceleration
        terms are assumed negligible.

        If both balls are non-translating, or if the midpoint (collision point) shifts
        by more than 5x the spacer (which can occur if balls are moving with nearly the
        same velocity), a naive fallback strategy is used that moves the balls
        uniformly along the line of centers until they're separated by an amount
        ``spacer``.

        Algorithm:
            1. If both balls are non-translating, apply fallback
            2. Otherwise, calculate quadratic coefficients for separation equation
            3. Solve for time offset that achieves target separation
            4. Move balls to corrected positions: r_new = r + t * v
            5. If midpoint shifts more than 5x spacer, apply fallback

        Returns:
            tuple[Ball, Ball]:
                ``ball1`` and ``ball2`` modified in place with adjusted positions.
        """
        r1 = ball1.state.rvw[0]
        r2 = ball2.state.rvw[0]
        v1 = ball1.state.rvw[1]
        v2 = ball2.state.rvw[1]

        spacer = const.MIN_DIST

        if (
            ball1.state.s in const.nontranslating
            and ball2.state.s in const.nontranslating
        ):
            r1_corrected, r2_corrected = self._apply_fallback_positioning(
                ball1, ball2, r1, r2, spacer
            )
        else:
            Bx = v2[0] - v1[0]
            By = v2[1] - v1[1]
            Bz = v2[2] - v1[2]
            Cx = r2[0] - r1[0]
            Cy = r2[1] - r1[1]
            Cz = r2[2] - r1[2]
            alpha = Bx * Bx + By * By + Bz * Bz
            beta = 2 * Bx * Cx + 2 * By * Cy + 2 * Bz * Cz
            gamma = (
                Cx * Cx
                + Cy * Cy
                + Cz * Cz
                - (2 * ball1.params.R + spacer) * (2 * ball1.params.R + spacer)
            )
            roots_complex = ptmath.roots.quadratic.solve_complex(alpha, beta, gamma)

            imag_mag = np.abs(roots_complex.imag)
            real_mag = np.abs(roots_complex.real)
            keep = (imag_mag / real_mag) < 1e-3
            roots = roots_complex[keep].real
            t = roots[np.abs(roots).argmin()]

            r1_corrected = r1 + t * v1
            r2_corrected = r2 + t * v2

            midpoint = (r1 + r2) / 2
            midpoint_corrected = (r1_corrected + r2_corrected) / 2
            if ptmath.norm3d(midpoint - midpoint_corrected) > 5 * spacer:
                r1_corrected, r2_corrected = self._apply_fallback_positioning(
                    ball1, ball2, r1, r2, spacer
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
