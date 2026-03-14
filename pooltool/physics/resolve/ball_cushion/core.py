from abc import ABC, abstractmethod
from typing import Protocol

import numpy as np

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.table.components import (
    CircularCushionSegment,
    LinearCushionSegment,
)


class _BaseLinearStrategy(Protocol):
    def make_kiss(self, ball: Ball, cushion: LinearCushionSegment) -> Ball: ...

    def resolve(
        self, ball: Ball, cushion: LinearCushionSegment, inplace: bool = False
    ) -> tuple[Ball, LinearCushionSegment]: ...


class _BaseCircularStrategy(Protocol):
    def make_kiss(self, ball: Ball, cushion: CircularCushionSegment) -> Ball: ...

    def resolve(
        self, ball: Ball, cushion: CircularCushionSegment, inplace: bool = False
    ) -> tuple[Ball, CircularCushionSegment]: ...


class BallLCushionCollisionStrategy(_BaseLinearStrategy, Protocol):
    """Ball-linear cushion collision models must satisfy this protocol"""

    def solve(
        self, ball: Ball, cushion: LinearCushionSegment
    ) -> tuple[Ball, LinearCushionSegment]:
        """This method resolves a ball-circular cushion collision"""
        ...


class BallCCushionCollisionStrategy(_BaseCircularStrategy, Protocol):
    """Ball-circular cushion collision models must satisfy this protocol"""

    def solve(
        self, ball: Ball, cushion: CircularCushionSegment
    ) -> tuple[Ball, CircularCushionSegment]:
        """This method resolves a ball-circular cushion collision"""
        ...


class CoreBallLCushionCollision(ABC):
    """Operations used by every ball-linear cushion collision resolver"""

    def _apply_fallback_positioning_linear(
        self, ball: Ball, cushion: LinearCushionSegment, spacer: float
    ) -> np.ndarray:
        """Place the ball at R + spacer from the cushion along the geometric normal.

        Used when the ball is nontranslating (no velocity to trace back along) or
        when the velocity-based correction would produce an excessive displacement.
        """
        c = ptmath.point_on_line_closest_to_point(
            cushion.p1, cushion.p2, ball.state.rvw[0]
        )
        c[2] = ball.state.rvw[0, 2]
        direction = ptmath.unit_vector(ball.state.rvw[0] - c)
        return c + (ball.params.R + spacer) * direction

    def make_kiss(self, ball: Ball, cushion: LinearCushionSegment) -> Ball:
        """Translate the ball along its velocity so it nearly touches the cushion.

        Solves a linear equation for the time offset t such that the ball's
        perpendicular distance to the cushion line equals R + spacer, then moves
        the ball to r + t * v. The perpendicular distance to a line is linear in t,
        so no quadratic solver is needed.

        If the ball is nontranslating or the displacement would exceed 5 * spacer,
        falls back to positioning along the geometric normal.
        """
        r = ball.state.rvw[0]
        v = ball.state.rvw[1]
        R = ball.params.R
        spacer = const.MIN_DIST

        if ball.state.s in const.nontranslating:
            ball.state.rvw[0] = self._apply_fallback_positioning_linear(
                ball, cushion, spacer
            )
            return ball

        n = cushion.get_normal_xy(ball.xyz)
        n = n if np.dot(n, v) > 0 else -n

        d0 = np.dot(r - cushion.p1, n)
        vn = np.dot(v, n)

        t1 = (R + spacer - d0) / vn
        t2 = (-(R + spacer) - d0) / vn
        t = t1 if abs(t1) < abs(t2) else t2

        if ptmath.norm3d(t * v) > 5 * spacer:
            ball.state.rvw[0] = self._apply_fallback_positioning_linear(
                ball, cushion, spacer
            )
            return ball

        ball.state.rvw[0] = r + t * v
        return ball

    def resolve(
        self, ball: Ball, cushion: LinearCushionSegment, inplace: bool = False
    ) -> tuple[Ball, LinearCushionSegment]:
        if not inplace:
            ball = ball.copy()
            cushion = cushion.copy()

        ball = self.make_kiss(ball, cushion)

        return self.solve(ball, cushion)

    @abstractmethod
    def solve(
        self, ball: Ball, cushion: LinearCushionSegment
    ) -> tuple[Ball, LinearCushionSegment]:
        pass


class CoreBallCCushionCollision(ABC):
    """Operations used by every ball-circular cushion collision resolver"""

    def _apply_fallback_positioning_circular(
        self, ball: Ball, cushion: CircularCushionSegment, spacer: float
    ) -> np.ndarray:
        """Place the ball at R + radius + spacer from the cushion center along the radial.

        Used when the ball is nontranslating (no velocity to trace back along) or
        when the velocity-based correction would produce an excessive displacement.
        """
        c = np.array([cushion.center[0], cushion.center[1], ball.state.rvw[0, 2]])
        direction = ptmath.unit_vector(ball.state.rvw[0] - c)
        return c + (ball.params.R + cushion.radius + spacer) * direction

    def make_kiss(self, ball: Ball, cushion: CircularCushionSegment) -> Ball:
        """Translate the ball along its velocity so it nearly touches the cushion.

        Solves a quadratic equation for the time offset t such that the ball's
        XY distance to the cushion center equals R + radius + spacer, then moves
        the ball to r + t * v. The smallest-magnitude real root is chosen.

        If the ball is nontranslating or the displacement would exceed 5 * spacer,
        falls back to positioning along the radial direction.
        """
        r = ball.state.rvw[0]
        v = ball.state.rvw[1]
        R = ball.params.R
        spacer = const.MIN_DIST

        if ball.state.s in const.nontranslating:
            ball.state.rvw[0] = self._apply_fallback_positioning_circular(
                ball, cushion, spacer
            )
            return ball

        c = np.array([cushion.center[0], cushion.center[1], r[2]])
        diff = r - c
        target = R + cushion.radius + spacer

        alpha = v[0] ** 2 + v[1] ** 2
        beta = 2 * (diff[0] * v[0] + diff[1] * v[1])
        gamma = diff[0] ** 2 + diff[1] ** 2 - target**2

        roots_complex = ptmath.roots.quadratic.solve_complex(alpha, beta, gamma)

        imag_mag = np.abs(roots_complex.imag)
        real_mag = np.abs(roots_complex.real)
        keep = (imag_mag / real_mag) < 1e-3
        roots = roots_complex[keep].real
        t = roots[np.abs(roots).argmin()]

        if ptmath.norm3d(t * v) > 5 * spacer:
            ball.state.rvw[0] = self._apply_fallback_positioning_circular(
                ball, cushion, spacer
            )
            return ball

        ball.state.rvw[0] = r + t * v
        return ball

    def resolve(
        self, ball: Ball, cushion: CircularCushionSegment, inplace: bool = False
    ) -> tuple[Ball, CircularCushionSegment]:
        if not inplace:
            ball = ball.copy()
            cushion = cushion.copy()

        ball = self.make_kiss(ball, cushion)

        return self.solve(ball, cushion)  # type: ignore
