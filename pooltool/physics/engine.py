from __future__ import annotations

from typing import Dict, Tuple

import attrs
import numpy as np

import pooltool.constants as c
import pooltool.constants as const
import pooltool.math as math
import pooltool.physics as physics
from pooltool.events.datatypes import AgentType, Event, EventType
from pooltool.objects.ball.datatypes import Ball, BallState
from pooltool.objects.cue.datatypes import Cue
from pooltool.objects.table.components import (
    CircularCushionSegment,
    LinearCushionSegment,
    Pocket,
)
from pooltool.system.datatypes import System


def resolve_ball_ball(
    ball1: Ball, ball2: Ball, inplace: bool = False
) -> Tuple[Ball, Ball]:
    if not inplace:
        ball1 = ball1.copy()
        ball2 = ball2.copy()

    rvw1, rvw2 = _resolve_ball_ball_collision(
        ball1.state.rvw.copy(),
        ball2.state.rvw.copy(),
        ball1.params.R,
    )

    ball1.state = BallState(rvw1, c.sliding)
    ball2.state = BallState(rvw2, c.sliding)

    return ball1, ball2


def resolve_linear_ball_cushion(
    ball: Ball, cushion: LinearCushionSegment, inplace: bool = False
) -> Tuple[Ball, LinearCushionSegment]:
    if not inplace:
        ball = ball.copy()
        cushion = cushion.copy()

    rvw = ball.state.rvw
    normal = cushion.get_normal(rvw)

    rvw = _resolve_ball_linear_cushion_collision(
        rvw=rvw,
        normal=normal,
        p1=cushion.p1,
        p2=cushion.p2,
        R=ball.params.R,
        m=ball.params.m,
        h=cushion.height,
        e_c=ball.params.e_c,
        f_c=ball.params.f_c,
    )

    ball.state = BallState(rvw, c.sliding)

    return ball, cushion


def resolve_circular_ball_cushion(
    ball: Ball, cushion: CircularCushionSegment, inplace: bool = False
) -> Tuple[Ball, CircularCushionSegment]:
    if not inplace:
        ball = ball.copy()
        cushion = cushion.copy()

    rvw = ball.state.rvw
    normal = cushion.get_normal(rvw)

    rvw = _resolve_ball_circular_cushion_collision(
        rvw=rvw,
        normal=normal,
        center=cushion.center,
        radius=cushion.radius,
        R=ball.params.R,
        m=ball.params.m,
        h=cushion.height,
        e_c=ball.params.e_c,
        f_c=ball.params.f_c,
    )

    ball.state = BallState(rvw, c.sliding)

    return ball, cushion


def resolve_ball_pocket(
    ball: Ball, pocket: Pocket, inplace: bool = False
) -> Tuple[Ball, Pocket]:
    if not inplace:
        ball = ball.copy()
        pocket = pocket.copy()

    # Ball is placed at the pocket center
    rvw = np.array(
        [
            [pocket.a, pocket.b, -pocket.depth],
            [0, 0, 0],
            [0, 0, 0],
        ]
    )

    ball.state = BallState(rvw, c.pocketed)
    pocket.add(ball.id)

    return ball, pocket


def resolve_stick_ball(cue: Cue, ball: Ball, inplace: bool = False) -> Tuple[Cue, Ball]:
    if not inplace:
        cue = cue.copy()
        ball = ball.copy()

    v, w = physics.cue_strike(
        ball.params.m,
        cue.specs.M,
        ball.params.R,
        cue.V0,
        cue.phi,
        cue.theta,
        cue.a,
        cue.b,
    )

    rvw = np.array([ball.state.rvw[0], v, w])
    s = c.sliding

    ball.state = BallState(rvw, s)

    return cue, ball


def resolve_transition(
    ball: Ball, transition: EventType, inplace: bool = False
) -> Ball:
    if not inplace:
        ball = ball.copy()

    assert transition.is_transition()
    start, end = _ball_transition_motion_states(transition)

    assert ball.state.s == start, f"Start state was {ball.state.s}, expected {start}"
    ball.state.s = end

    if end == c.spinning:
        # Assert that the velocity components are nearly 0, and that the x and y angular
        # velocity components are nearly 0. Then set them to exactly 0.
        v = ball.state.rvw[1]
        w = ball.state.rvw[2]
        assert (np.abs(v) < c.EPS_SPACE).all()
        assert (np.abs(w[:2]) < c.EPS_SPACE).all()

        ball.state.rvw[1, :] = [0.0, 0.0, 0.0]
        ball.state.rvw[2, :2] = [0.0, 0.0]

    if end == c.stationary:
        # Assert that the linear and angular velocity components are nearly 0, then set
        # them to exactly 0.
        v = ball.state.rvw[1]
        w = ball.state.rvw[2]
        assert (np.abs(v) < c.EPS_SPACE).all()
        assert (np.abs(w) < c.EPS_SPACE).all()

        ball.state.rvw[1, :] = [0.0, 0.0, 0.0]
        ball.state.rvw[2, :] = [0.0, 0.0, 0.0]

    return ball


def _ball_transition_motion_states(event_type: EventType) -> Tuple[int, int]:
    """Return the ball motion states before and after a transition"""
    assert event_type.is_transition()

    if event_type == EventType.SPINNING_STATIONARY:
        return c.spinning, c.stationary
    elif event_type == EventType.ROLLING_STATIONARY:
        return c.rolling, c.stationary
    elif event_type == EventType.ROLLING_SPINNING:
        return c.rolling, c.spinning
    elif event_type == EventType.SLIDING_ROLLING:
        return c.sliding, c.rolling

    raise NotImplementedError()


@attrs.define
class Resolver:
    placeholder: str = attrs.field(default="dummy")

    @classmethod
    def default(cls) -> Resolver:
        return cls()


@attrs.define
class PhysicsEngine:
    resolver: Resolver = attrs.field(factory=Resolver.default)

    def snapshot_initial(self, shot: System, event: Event) -> None:
        """Set the initial states of the event agents"""
        for agent in event.agents:
            if agent.agent_type == AgentType.CUE:
                agent.set_initial(shot.cue)
            elif agent.agent_type == AgentType.BALL:
                agent.set_initial(shot.balls[agent.id])
            elif agent.agent_type == AgentType.POCKET:
                agent.set_initial(shot.table.pockets[agent.id])
            elif agent.agent_type == AgentType.LINEAR_CUSHION_SEGMENT:
                agent.set_initial(shot.table.cushion_segments.linear[agent.id])
            elif agent.agent_type == AgentType.CIRCULAR_CUSHION_SEGMENT:
                agent.set_initial(shot.table.cushion_segments.circular[agent.id])

    def snapshot_final(self, shot: System, event: Event) -> None:
        """Set the final states of the event agents"""
        for agent in event.agents:
            if agent.agent_type == AgentType.BALL:
                agent.set_final(shot.balls[agent.id])
            elif agent.agent_type == AgentType.POCKET:
                agent.set_final(shot.table.pockets[agent.id])

    def resolve_event(self, shot: System, event: Event) -> None:
        self.snapshot_initial(shot, event)

        ids = event.ids

        if event.event_type == EventType.NONE:
            return
        elif event.event_type.is_transition():
            ball = shot.balls[ids[0]]
            _ = resolve_transition(ball, event.event_type, inplace=True)
        elif event.event_type == EventType.BALL_BALL:
            ball1 = shot.balls[ids[0]]
            ball2 = shot.balls[ids[1]]
            _ = resolve_ball_ball(ball1, ball2, inplace=True)
            ball1.state.t = event.time
            ball2.state.t = event.time
        elif event.event_type == EventType.BALL_LINEAR_CUSHION:
            ball = shot.balls[ids[0]]
            cushion = shot.table.cushion_segments.linear[ids[1]]
            _ = resolve_linear_ball_cushion(ball, cushion, inplace=True)
            ball.state.t = event.time
        elif event.event_type == EventType.BALL_CIRCULAR_CUSHION:
            ball = shot.balls[ids[0]]
            cushion_jaw = shot.table.cushion_segments.circular[ids[1]]
            _ = resolve_circular_ball_cushion(ball, cushion_jaw, inplace=True)
            ball.state.t = event.time
        elif event.event_type == EventType.BALL_POCKET:
            ball = shot.balls[ids[0]]
            pocket = shot.table.pockets[ids[1]]
            _ = resolve_ball_pocket(ball, pocket, inplace=True)
            ball.state.t = event.time
        elif event.event_type == EventType.STICK_BALL:
            cue = shot.cue
            ball = shot.balls[ids[1]]
            _ = resolve_stick_ball(cue, ball, inplace=True)
            ball.state.t = event.time

        self.snapshot_final(shot, event)


def _resolve_ball_ball_collision(rvw1, rvw2, R, spacer: bool = True):
    """Instantaneous, elastic, equal mass collision

    Args:
        spacer:
            A correction is made such that if the balls are not 2*R apart, they are
            moved equally along their line of centers such that they are, at least to
            within float precision error. That's where this paramter comes in. If spacer
            is True, a small epsilon of additional distance (constants.EPS_SPACE) is put
            between them, ensuring the balls are non-intersecting.
    """

    r1, r2 = rvw1[0], rvw2[0]
    v1, v2 = rvw1[1], rvw2[1]

    n = math.unit_vector(r2 - r1)
    t = math.coordinate_rotation(n, np.pi / 2)

    correction = 2 * R - math.norm3d(r2 - r1) + (const.EPS_SPACE if spacer else 0.0)
    rvw2[0] += correction / 2 * n
    rvw1[0] -= correction / 2 * n

    v_rel = v1 - v2
    v_mag = math.norm3d(v_rel)

    beta = math.angle(v_rel, n)

    rvw1[1] = t * v_mag * np.sin(beta) + v2
    rvw2[1] = n * v_mag * np.cos(beta) + v2

    return rvw1, rvw2


def _resolve_ball_linear_cushion_collision(
    rvw, normal, p1, p2, R, m, h, e_c, f_c, spacer: bool = True
):
    """Resolve the ball linear cushion collision

    Args:
        spacer:
            A correction is made such that if the ball is not a distance R from the
            cushion, the ball is moved along the normal such that it is, at least to
            within float precision error. That's where this paramter comes in. If spacer
            is True, a small epsilon of additional distance (constants.EPS_SPACE) is put
            between them, ensuring the cushion and ball are separated post-resolution.
    """
    # orient the normal so it points away from playing surface
    normal = normal if np.dot(normal, rvw[1]) > 0 else -normal

    rvw = _resolve_ball_cushion_collision(rvw, normal, R, m, h, e_c, f_c)

    # Calculate the point on cushion line where contact should be made, then set the
    # z-component to match the ball's height
    c = math.point_on_line_closest_to_point(p1, p2, rvw[0])
    c[2] = rvw[0, 2]

    # Move the ball to meet the cushion
    correction = R - math.norm3d(rvw[0] - c) + (const.EPS_SPACE if spacer else 0.0)
    rvw[0] -= correction * normal

    return rvw


def _resolve_ball_cushion_collision(rvw, normal, R, m, h, e_c, f_c):
    """Inhwan Han (2005) 'Dynamics in Carom and Three Cushion Billiards'"""

    # Change from the table frame to the cushion frame. The cushion frame is defined by
    # the normal vector is parallel with <1,0,0>.
    psi = math.angle(normal)
    rvw_R = math.coordinate_rotation(rvw.T, -psi).T

    # The incidence angle--called theta_0 in paper
    phi = math.angle(rvw_R[1]) % (2 * np.pi)

    # Get mu and e
    e = get_ball_cushion_restitution(rvw_R, e_c)
    mu = get_ball_cushion_friction(rvw_R, f_c)

    # Depends on height of cushion relative to ball
    theta_a = np.arcsin(h / R - 1)

    # Eqs 14
    sx = rvw_R[1, 0] * np.sin(theta_a) - rvw_R[1, 2] * np.cos(theta_a) + R * rvw_R[2, 1]
    sy = (
        -rvw_R[1, 1]
        - R * rvw_R[2, 2] * np.cos(theta_a)
        + R * rvw_R[2, 0] * np.sin(theta_a)
    )
    c = rvw_R[1, 0] * np.cos(theta_a)  # 2D assumption

    # Eqs 16
    I = 2 / 5 * m * R**2
    A = 7 / 2 / m
    B = 1 / m

    # Eqs 17 & 20
    PzE = (1 + e) * c / B
    PzS = np.sqrt(sx**2 + sy**2) / A

    if PzS <= PzE:
        # Sliding and sticking case
        PX = -sx / A * np.sin(theta_a) - (1 + e) * c / B * np.cos(theta_a)
        PY = sy / A
        PZ = sx / A * np.cos(theta_a) - (1 + e) * c / B * np.sin(theta_a)
    else:
        # Forward sliding case
        PX = -mu * (1 + e) * c / B * np.cos(phi) * np.sin(theta_a) - (
            1 + e
        ) * c / B * np.cos(theta_a)
        PY = mu * (1 + e) * c / B * np.sin(phi)
        PZ = mu * (1 + e) * c / B * np.cos(phi) * np.cos(theta_a) - (
            1 + e
        ) * c / B * np.sin(theta_a)

    # Update velocity
    rvw_R[1, 0] += PX / m
    rvw_R[1, 1] += PY / m
    # rvw_R[1,2] += PZ/m

    # Update angular velocity
    rvw_R[2, 0] += -R / I * PY * np.sin(theta_a)
    rvw_R[2, 1] += R / I * (PX * np.sin(theta_a) - PZ * np.cos(theta_a))
    rvw_R[2, 2] += R / I * PY * np.cos(theta_a)

    # Change back to table reference frame
    rvw = math.coordinate_rotation(rvw_R.T, psi).T

    return rvw


def get_ball_cushion_restitution(rvw, e_c):
    """Get restitution coefficient dependent on ball state

    Parameters
    ==========
    rvw: np.array
        Assumed to be in reference frame such that <1,0,0> points
        perpendicular to the cushion, and in the direction away from the table

    Notes
    =====
    - https://essay.utwente.nl/59134/1/scriptie_J_van_Balen.pdf suggests a constant
      value of 0.85
    """

    return e_c
    return max([0.40, 0.50 + 0.257 * rvw[1, 0] - 0.044 * rvw[1, 0] ** 2])


def get_ball_cushion_friction(rvw, f_c):
    """Get friction coeffecient depend on ball state

    Parameters
    ==========
    rvw: np.array
        Assumed to be in reference frame such that <1,0,0> points
        perpendicular to the cushion, and in the direction away from the table
    """

    ang = math.angle(rvw[1])

    if ang > np.pi:
        ang = np.abs(2 * np.pi - ang)

    ans = f_c
    return ans


def _resolve_ball_circular_cushion_collision(
    rvw, normal, center, radius, R, m, h, e_c, f_c, spacer: bool = True
):
    """Resolve the ball linear cushion collision

    Args:
        spacer:
            A correction is made such that if the ball is not a distance R from the
            cushion, the ball is moved along the normal such that it is, at least to
            within float precision error. That's where this paramter comes in. If spacer
            is True, a small epsilon of additional distance (constants.EPS_SPACE) is put
            between them, ensuring the cushion and ball are separated post-resolution.
    """
    # orient the normal so it points away from playing surface
    normal = normal if np.dot(normal, rvw[1]) > 0 else -normal

    rvw = _resolve_ball_cushion_collision(rvw, normal, R, m, h, e_c, f_c)

    c = np.array([center[0], center[1], rvw[0, 2]])
    correction = (
        R + radius - math.norm3d(rvw[0] - c) - (const.EPS_SPACE if spacer else 0.0)
    )

    rvw[0] += correction * normal

    return rvw
