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

        Solves a quadratic equation for the time offset t such that the ball's
        perpendicular distance to the cushion line equals R + spacer, then moves
        the ball to r + t * v. The smallest-magnitude real root is chosen.

        If the ball is nontranslating or the displacement would exceed
        FALLBACK_DISPLACEMENT_FACTOR * spacer (e.g. on a near-grazing trajectory,
        or when the ball's velocity is parallel to the cushion axis), falls back to
        positioning along the perpendicular from the cushion line.
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
        target = R + spacer

        alpha = np.dot(v_perp, v_perp)
        beta = 2 * np.dot(q0_perp, v_perp)
        gamma = np.dot(q0_perp, q0_perp) - target**2

        roots_complex = ptmath.roots.quadratic.solve(alpha, beta, gamma)
        t = ptmath.roots.get_real_smallest_magnitude_root(roots_complex)

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
            return _apply_fallback_positioning_circular(ball, cushion, spacer)

        c = np.array([cushion.center[0], cushion.center[1], r[2]])
        diff = r - c
        target = R + cushion.radius + spacer

        alpha = v[0] ** 2 + v[1] ** 2
        beta = 2 * (diff[0] * v[0] + diff[1] * v[1])
        gamma = diff[0] ** 2 + diff[1] ** 2 - target**2

        roots_complex = ptmath.roots.quadratic.solve(alpha, beta, gamma)
        t = ptmath.roots.get_real_smallest_magnitude_root(roots_complex)

        if ptmath.norm3d(t * v) > FALLBACK_DISPLACEMENT_FACTOR * spacer:
            return _apply_fallback_positioning_circular(ball, cushion, spacer)

        ball.state.rvw[0] = _clamp_to_table(r + t * v, R)

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
    """Place the ball at R + spacer from the cushion line along the perpendicular.

    Used when the ball is nontranslating (no velocity to trace back along) or
    when the velocity-based correction would produce an excessive displacement.
    """
    R = ball.params.R
    c = ptmath.point_on_line_closest_to_point(cushion.p1, cushion.p2, ball.state.rvw[0])
    direction = ptmath.unit_vector(ball.state.rvw[0] - c)
    candidate = c + (R + spacer) * direction
    ball.state.rvw[0] = _constrain_to_table(
        candidate, cushion, R, airborne=ball.state.s == const.airborne
    )

    return ball


def _clamp_to_table(pos: np.ndarray, R: float) -> np.ndarray:
    """Raise ``pos[2]`` to ``R`` if below, leave unchanged otherwise.

    For vertical-axis cushions (the current circular cushion model), this preserves
    distance from the cushion axis since the axis runs along z.
    """
    if pos[2] >= R:
        return pos
    new_pos = pos.copy()
    new_pos[2] = R
    return new_pos


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
    ball on its original side around the axis.
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
    b = np.sign(np.dot(direction, h_hat)) * np.sqrt(1.0 - a * a)
    new_direction = a * z_hat + b * h_hat

    return c + arm_len * new_direction


def _apply_fallback_positioning_circular(
    ball: Ball, cushion: CircularCushionSegment, spacer: float
) -> Ball:
    """Place the ball at R + radius + spacer from the cushion center along the radial.

    Used when the ball is nontranslating (no velocity to trace back along) or
    when the velocity-based correction would produce an excessive displacement.
    """
    c = np.array([cushion.center[0], cushion.center[1], ball.state.rvw[0, 2]])
    direction = ptmath.unit_vector(ball.state.rvw[0] - c)
    ball.state.rvw[0] = c + (ball.params.R + cushion.radius + spacer) * direction

    return ball
