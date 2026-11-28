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
from pooltool.physics.dimensionality import Dim

FALLBACK_DISPLACEMENT_FACTOR = 5
"""Multiplier on ``spacer`` defining the max make_kiss displacement before falling back.

If the velocity-based correction would move the ball more than
``FALLBACK_DISPLACEMENT_FACTOR * spacer`` (e.g. on a near-grazing trajectory), make_kiss
falls back to positioning along the cushion normal instead.
"""

NEWTON_MAX_ITER = 10
NEWTON_TOL = 1e-12


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

    dim: Dim

    def solve(
        self, ball: Ball, cushion: LinearCushionSegment
    ) -> tuple[Ball, LinearCushionSegment]:
        """This method resolves a ball-circular cushion collision"""
        ...


class BallCCushionCollisionStrategy(_BaseCircularStrategy, Protocol):
    """Ball-circular cushion collision models must satisfy this protocol"""

    dim: Dim

    def solve(
        self, ball: Ball, cushion: CircularCushionSegment
    ) -> tuple[Ball, CircularCushionSegment]:
        """This method resolves a ball-circular cushion collision"""
        ...


class CoreBallLCushionCollision(ABC):
    """Operations used by every ball-linear cushion collision resolver"""

    def make_kiss(self, ball: Ball, cushion: LinearCushionSegment) -> Ball:
        """Translate the ball along its velocity so it nearly touches the cushion.

        The cushion is modeled as a thin cylinder of radius ``cushion.nose_radius``
        around the line through ``p1`` and ``p2``. Solves a quadratic equation for
        the time offset t such that the ball's perpendicular distance to the
        cushion line equals ``R + nose_radius + spacer``, then moves the ball to
        ``r + t * v``. The smallest-magnitude real root is chosen.

        If the ball is nontranslating, if the quadratic has no real root (which
        happens when the velocity is parallel to the cushion axis, leaving no
        perpendicular component to travel along), or if the displacement would exceed
        FALLBACK_DISPLACEMENT_FACTOR * spacer (e.g. on a near-grazing trajectory),
        falls back to positioning along the perpendicular from the cushion line.
        """
        r = ball.state.rvw[0]
        v = ball.state.rvw[1]
        R = ball.params.R
        spacer = const.MIN_DIST

        if ball.state.s in const.nontranslating:
            return _apply_fallback_positioning_linear(ball, cushion, spacer)

        u = cushion.unit_axis
        q0 = r - cushion.p1
        v_perp = v - np.dot(v, u) * u
        q0_perp = q0 - np.dot(q0, u) * u
        target = R + cushion.nose_radius + spacer

        alpha = np.dot(v_perp, v_perp)
        beta = 2 * np.dot(q0_perp, v_perp)
        gamma = np.dot(q0_perp, q0_perp) - target**2

        roots_complex = ptmath.roots.quadratic.solve(alpha, beta, gamma)
        t = ptmath.roots.get_real_smallest_magnitude_root(
            roots_complex,
            ptmath.roots.ABS_OR_REL_CUTOFF,
            ptmath.roots.RTOL,
            ptmath.roots.ATOL,
        )

        if not np.isfinite(t):
            return _apply_fallback_positioning_linear(ball, cushion, spacer)

        if ptmath.norm3d(t * v) > FALLBACK_DISPLACEMENT_FACTOR * spacer:
            return _apply_fallback_positioning_linear(ball, cushion, spacer)

        ball.state.rvw[0] = _constrain_to_table(
            r + t * v, cushion, R, airborne=ball.state.s == const.airborne
        )

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

    def make_kiss(self, ball: Ball, cushion: CircularCushionSegment) -> Ball:
        """Translate the ball along its velocity so it nearly touches the cushion.

        The cushion nose is a tube of radius ``cushion.nose_radius`` around the nose
        circle of radius ``cushion.radius``. Newton's method on the time
        offset t finds where the distance from the ball's center to the nose circle
        equals ``R + nose_radius + spacer``, then the ball moves to ``r + t * v``.
        Starting from t = 0 selects the nearest such offset. A ball on the table has
        no vertical velocity, so for it this is the horizontal rewind to the
        effective contact radius the detector uses.

        If the ball is nontranslating, if Newton does not converge (velocity nearly
        tangent to the surface), or if the displacement would exceed
        FALLBACK_DISPLACEMENT_FACTOR * spacer, falls back to positioning along the
        surface normal.
        """
        r = ball.state.rvw[0]
        v = ball.state.rvw[1]
        R = ball.params.R
        spacer = const.MIN_DIST
        target = R + cushion.nose_radius + spacer

        if ball.state.s in const.nontranslating:
            return _apply_fallback_positioning_circular(ball, cushion, spacer)

        t = 0.0
        converged = False
        for _ in range(NEWTON_MAX_ITER):
            pos = r + t * v
            offset = pos - cushion.nearest_nose_point(pos)
            dist = ptmath.norm3d(offset)
            if dist == 0.0:
                break
            residual = dist - target
            if abs(residual) < NEWTON_TOL:
                converged = True
                break
            slope = np.dot(offset, v) / dist
            if slope == 0.0:
                break
            t -= residual / slope

        if not converged:
            return _apply_fallback_positioning_circular(ball, cushion, spacer)

        if ptmath.norm3d(t * v) > FALLBACK_DISPLACEMENT_FACTOR * spacer:
            return _apply_fallback_positioning_circular(ball, cushion, spacer)

        ball.state.rvw[0] = _constrain_to_table_circular(
            r + t * v, cushion, R, target, airborne=ball.state.s == const.airborne
        )

        return ball

    def resolve(
        self, ball: Ball, cushion: CircularCushionSegment, inplace: bool = False
    ) -> tuple[Ball, CircularCushionSegment]:
        if not inplace:
            ball = ball.copy()
            cushion = cushion.copy()

        ball = self.make_kiss(ball, cushion)

        return self.solve(ball, cushion)  # type: ignore


def _apply_fallback_positioning_linear(
    ball: Ball, cushion: LinearCushionSegment, spacer: float
) -> Ball:
    """Place the ball at R + nose_radius + spacer from the cushion line along the perpendicular.

    Used when the ball is nontranslating (no velocity to trace back along) or
    when the velocity-based correction would produce an excessive displacement.
    """
    R = ball.params.R
    c = ptmath.point_on_line_closest_to_point(cushion.p1, cushion.p2, ball.state.rvw[0])
    direction = ptmath.unit_vector(ball.state.rvw[0] - c)
    candidate = c + (R + cushion.nose_radius + spacer) * direction
    ball.state.rvw[0] = _constrain_to_table(
        candidate, cushion, R, airborne=ball.state.s == const.airborne
    )

    return ball


def _constrain_to_table(
    pos: np.ndarray,
    cushion: LinearCushionSegment,
    R: float,
    airborne: bool,
) -> np.ndarray:
    """Rotate ``pos`` around the cushion axis to enforce the ball's table constraint.

    For non-airborne balls, the constraint is ``z == R`` exactly: the ball must rest on
    the table. The perpendicular from the cushion line can place the candidate either
    above or below R, and both directions need correcting — above is unphysical lift
    (artificial PE gain), below is table penetration.

    For airborne balls, the constraint is ``z >= R``: only lift when below R.

    The rotation preserves the arm length (distance from cushion line) and keeps the
    ball on its original side around the axis. When the ball sits exactly on the
    vertical through the cushion axis it has no side to preserve, and the positive
    side is chosen arbitrarily.
    """
    if airborne and pos[2] >= R:
        return pos

    if pos[2] == R:
        return pos

    c = ptmath.point_on_line_closest_to_point(cushion.p1, cushion.p2, pos)
    arm = pos - c
    arm_len = ptmath.norm3d(arm)
    direction = arm / arm_len

    u = cushion.unit_axis
    z_hat = np.array([0.0, 0.0, 1.0])
    h_hat = np.array([u[1], -u[0], 0.0])

    a = (R - c[2]) / arm_len
    side = 1.0 if np.dot(direction, h_hat) >= 0 else -1.0
    b = side * np.sqrt(1.0 - a * a)
    new_direction = a * z_hat + b * h_hat

    return c + arm_len * new_direction


def _apply_fallback_positioning_circular(
    ball: Ball, cushion: CircularCushionSegment, spacer: float
) -> Ball:
    """Place the ball R + nose_radius + spacer from the nose circle along the surface normal.

    Used when the ball is nontranslating (no velocity to trace back along) or when
    the velocity-based correction fails or would produce an excessive displacement.
    """
    R = ball.params.R
    target = R + cushion.nose_radius + spacer
    pos = ball.state.rvw[0]
    candidate = cushion.nearest_nose_point(pos) + target * cushion.get_normal_3d(pos)
    ball.state.rvw[0] = _constrain_to_table_circular(
        candidate, cushion, R, target, airborne=ball.state.s == const.airborne
    )

    return ball


def _constrain_to_table_circular(
    pos: np.ndarray,
    cushion: CircularCushionSegment,
    R: float,
    target: float,
    airborne: bool,
) -> np.ndarray:
    """Rotate ``pos`` about the nose circle to enforce the ball's table constraint.

    For non-airborne balls, the constraint is ``z == R`` exactly: the ball must rest on
    the table. The surface normal tilts downward for a ball on the table, so the
    fallback can place the candidate above or below R, and both directions need
    correcting.

    For airborne balls, the constraint is ``z >= R``: only lift when below R.

    The rotation is in the meridian plane, so it preserves the ball's azimuth and its
    distance ``target`` to the nose circle: the ball lands at height ``R`` at the
    horizontal distance from the axis where a center at that height is ``target``
    away, on whichever side of the nose circle the ball already is.
    """
    if airborne and pos[2] >= R:
        return pos

    if pos[2] == R:
        return pos

    radial = np.array([pos[0] - cushion.center[0], pos[1] - cushion.center[1], 0.0])
    norm = ptmath.norm3d(radial)
    direction = radial / norm if norm > 0 else np.array([1.0, 0.0, 0.0])
    reach = np.sqrt(target**2 - (R - cushion.height) ** 2)
    horizontal = (
        cushion.radius - reach if norm < cushion.radius else cushion.radius + reach
    )
    placed = cushion.center + horizontal * direction
    placed[2] = R
    return placed
