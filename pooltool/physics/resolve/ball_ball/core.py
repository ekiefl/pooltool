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

    def resolve(
        self, ball1: Ball, ball2: Ball, inplace: bool = False
    ) -> tuple[Ball, Ball]:
        if not inplace:
            ball1 = ball1.copy()
            ball2 = ball2.copy()

        ball1, ball2 = self.make_kiss(ball1, ball2)
        ball1, ball2 = self.solve(ball1, ball2)

        return ball1, ball2

    @abstractmethod
    def solve(self, ball1: Ball, ball2: Ball) -> tuple[Ball, Ball]:
        pass
