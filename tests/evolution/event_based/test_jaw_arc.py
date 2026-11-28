"""Airborne jaw contact is restricted to the physical arc of the nose circle.

The fixture is a rounded convex corner of cushion. The body fills the quadrant
``x < 0, y < 0``; its two edges are perpendicular linear segments joined by a nose
circle tangent to both, so the quarter of the ring facing the open quadrant is
cushion and the other three quarters lie inside the body.
"""

import numpy as np
import pytest

import pooltool.constants as const
from pooltool.evolution.event_based.cache import CollisionCache
from pooltool.evolution.event_based.detect.ball_cushion import (
    get_next_ball_circular_cushion_event,
)
from pooltool.objects import Ball, BallParams, Cue, Table
from pooltool.objects.table.components import (
    CircularCushionSegment,
    CushionDirection,
    CushionSegments,
    LinearCushionSegment,
)
from pooltool.objects.table.specs import PocketTableSpecs, TableType
from pooltool.system import System

SPECS = PocketTableSpecs()
PARAMS = BallParams.default()
RING_RADIUS = 0.05
CENTER = np.array([-RING_RADIUS, -RING_RADIUS, SPECS.cushion_height])
TOUCH = PARAMS.R + SPECS.cushion_nose_radius
QUARTER = np.pi / 2
FULL_RING = 2 * np.pi


def corner_table(arc_span: float) -> Table:
    """The rounded corner, with ``arc_span`` radians of nose circle from azimuth 0."""
    h = SPECS.cushion_height
    nose = SPECS.cushion_nose_radius
    linear = {
        "top": LinearCushionSegment(
            "top",
            p1=np.array([-1.0, 0.0, h]),
            p2=np.array([-RING_RADIUS, 0.0, h]),
            nose_radius=nose,
            direction=CushionDirection.BOTH,
        ),
        "right": LinearCushionSegment(
            "right",
            p1=np.array([0.0, -1.0, h]),
            p2=np.array([0.0, -RING_RADIUS, h]),
            nose_radius=nose,
            direction=CushionDirection.BOTH,
        ),
    }
    jaw = CircularCushionSegment(
        "jaw",
        center=CENTER.copy(),
        radius=RING_RADIUS,
        nose_radius=nose,
        arc_start=0.0,
        arc_span=arc_span,
    )
    return Table(
        cushion_segments=CushionSegments(linear=linear, circular={"jaw": jaw}),
        pockets={},
        table_type=TableType.OTHER,
    )


def airborne_ball(
    xy: np.ndarray, height: float, velocity: tuple[float, float, float]
) -> Ball:
    """A ball in flight at ``height`` above the nose circle's plane."""
    ball = Ball.create("cue", xy=(xy[0], xy[1]))
    ball.state.rvw[0, 2] = CENTER[2] + height
    ball.state.rvw[1] = velocity
    ball.state.s = const.airborne
    return ball


def above_ring(azimuth: float) -> np.ndarray:
    return CENTER[:2] + RING_RADIUS * np.array([np.cos(azimuth), np.sin(azimuth)])


def jaw_contact_time(table: Table, ball: Ball) -> float:
    system = System(cue=Cue(cue_ball_id="cue"), table=table, balls={"cue": ball})
    return get_next_ball_circular_cushion_event(system, CollisionCache()).time


def position_at(ball: Ball, t: float) -> np.ndarray:
    gravity = np.array([0.0, 0.0, -0.5 * PARAMS.g * t * t])
    return ball.state.rvw[0] + ball.state.rvw[1] * t + gravity


def azimuth_of(xyz: np.ndarray) -> float:
    return np.arctan2(xyz[1] - CENTER[1], xyz[0] - CENTER[0]) % FULL_RING


def dist_to_nose_circle(xyz: np.ndarray) -> float:
    horizontal = np.hypot(xyz[0] - CENTER[0], xyz[1] - CENTER[1]) - RING_RADIUS
    return np.hypot(horizontal, xyz[2] - CENTER[2])


def test_drop_onto_the_arc_is_detected():
    ball = airborne_ball(above_ring(QUARTER / 2), 0.1, (0.0, 0.0, 0.0))

    t = jaw_contact_time(corner_table(QUARTER), ball)

    assert t == pytest.approx(np.sqrt(2 * (0.1 - TOUCH) / PARAMS.g), rel=1e-9)


@pytest.mark.parametrize("azimuth", [0.75 * np.pi, np.pi, 1.25 * np.pi, 1.5 * np.pi])
def test_drop_inside_the_body_is_not_detected(azimuth: float):
    """The ring under the body is not cushion, though the whole ring would catch it."""
    ball = airborne_ball(above_ring(azimuth), 0.1, (0.0, 0.0, 0.0))

    assert np.isfinite(jaw_contact_time(corner_table(FULL_RING), ball))
    assert jaw_contact_time(corner_table(QUARTER), ball) == np.inf


def test_path_through_the_body_contacts_the_arc_from_inside():
    """Entering the ring under the body is skipped; the arc is met from the inside.

    The ball flies through the axis at speed, so the first place the whole ring would
    stop it is its outer face under the body. On the arc, the first contact is the
    inner face of the nose on the far side.
    """
    speed = 10.0
    ball = airborne_ball(
        CENTER[:2] + np.array([-0.2, -0.2]),
        0.002,
        (speed / np.sqrt(2), speed / np.sqrt(2), 0.0),
    )

    phantom = jaw_contact_time(corner_table(FULL_RING), ball)
    t = jaw_contact_time(corner_table(QUARTER), ball)

    assert phantom < t < np.inf
    contact = position_at(ball, t)
    assert dist_to_nose_circle(contact) == pytest.approx(TOUCH, abs=1e-9)
    assert 0 <= azimuth_of(contact) <= QUARTER
    assert np.hypot(*(contact[:2] - CENTER[:2])) < RING_RADIUS
    assert azimuth_of(position_at(ball, phantom)) == pytest.approx(1.25 * np.pi)
