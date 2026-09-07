import numpy as np
import pytest

import pooltool.constants as const
from pooltool.evolution.event_based.detect.ball_cushion import (
    ball_linear_cushion_segment_collision_time,
    ball_vertical_plane_collision_time,
)
from pooltool.objects import Ball
from pooltool.objects.table.components import LinearCushionSegment
from pooltool.physics.evolve import evolve_ball_motion

HEIGHT = 0.64 * 2 * 0.028575


def _cushion(nose_radius: float) -> LinearCushionSegment:
    return LinearCushionSegment(
        id="c",
        p1=np.array([1.0, 0.0, HEIGHT]),
        p2=np.array([1.0, 1.0, HEIGHT]),
        nose_radius=nose_radius,
    )


def _ball(x: float, vx: float) -> Ball:
    ball = Ball.create("cue", xy=(x, 0.5))
    ball.state.rvw[1] = [vx, 0.0, 0.0]
    ball.state.s = const.sliding
    return ball


def _collision_time(ball: Ball, cushion: LinearCushionSegment) -> float:
    return ball_vertical_plane_collision_time(
        rvw=ball.state.rvw,
        s=ball.state.s,
        lx=cushion.lx,
        ly=cushion.ly,
        l0=cushion.l0,
        p1=cushion.p1,
        p2=cushion.p2,
        direction=cushion.direction,
        mu=ball.params.u_s,
        m=ball.params.m,
        g=ball.params.g,
        R=ball.params.R,
        nose_radius=cushion.nose_radius,
        height=cushion.height,
    )


def _contact_distance(ball: Ball, cushion: LinearCushionSegment) -> float:
    R = ball.params.R
    return np.sqrt((R + cushion.nose_radius) ** 2 - (cushion.height - R) ** 2)


@pytest.mark.parametrize("nose_radius", [0.001, 0.005])
def test_detection_matches_nose_cylinder_contact(nose_radius: float):
    """The ball is detected where its center touches the nose cylinder, not at R."""
    cushion = _cushion(nose_radius)
    ball = _ball(0.9, 1.0)

    t = _collision_time(ball, cushion)
    rvw, _ = evolve_ball_motion(
        ball.state.s,
        ball.state.rvw,
        ball.params.R,
        ball.params.m,
        ball.params.u_s,
        ball.params.u_sp,
        ball.params.u_r,
        ball.params.g,
        t,
    )

    assert 1.0 - rvw[0, 0] == pytest.approx(_contact_distance(ball, cushion))


def test_ball_inside_contact_band_moving_away_is_not_detected():
    """A ball left just inside the contact distance and receding never re-collides."""
    cushion = _cushion(0.001)
    ball = _ball(1.0, -1.0)
    ball.state.rvw[0, 0] = 1.0 - _contact_distance(ball, cushion) + 1e-4

    assert _collision_time(ball, cushion) == np.inf


def _collision_time_3d(ball: Ball, cushion: LinearCushionSegment) -> float:
    return ball_linear_cushion_segment_collision_time(ball, cushion)


def test_3d_detection_matches_nose_cylinder_contact():
    """The 3D detector also finds contact where the center meets the nose cylinder."""
    cushion = _cushion(0.001)
    ball = _ball(0.9, 1.0)

    t = _collision_time_3d(ball, cushion)
    rvw, _ = evolve_ball_motion(
        ball.state.s,
        ball.state.rvw,
        ball.params.R,
        ball.params.m,
        ball.params.u_s,
        ball.params.u_sp,
        ball.params.u_r,
        ball.params.g,
        t,
    )

    assert 1.0 - rvw[0, 0] == pytest.approx(_contact_distance(ball, cushion))


def test_3d_detection_ignores_the_line_beyond_the_segment():
    """A ball aimed past the end of a finite segment never collides with it."""
    cushion = _cushion(0.001)
    ball = _ball(0.9, 1.0)
    ball.state.rvw[0, 1] = 1.5

    assert _collision_time_3d(ball, cushion) == np.inf


def test_3d_detection_ignores_receding_airborne_ball_inside_nose_cylinder():
    """An airborne ball just inside the nose cylinder and flying away never collides."""
    cushion = _cushion(0.001)
    ball = _ball(1.0, -1.0)
    ball.state.rvw[0, 0] = 1.0 - (ball.params.R + cushion.nose_radius) + 1e-4
    ball.state.rvw[0, 2] = cushion.height
    ball.state.s = const.airborne

    assert _collision_time_3d(ball, cushion) == np.inf
