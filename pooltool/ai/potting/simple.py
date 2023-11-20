"""A simple aiming procedure

The concept of this aiming procedure is to determine the cueing angle phi such that the
cue ball contacts the object ball on the aim line. Cut- and spin-induced throw is
ignored. Bank shots are not supported. Interfering balls are not detected.
"""

import math
from typing import Dict, List, Optional, Sequence

import attrs
import numpy as np
from numpy.typing import NDArray

from pooltool.objects import Ball, Pocket, Table
from pooltool.ptmath import (
    angle_between_vectors,
    find_intersection_2D,
    norm3d,
    unit_vector,
    unit_vector_slow,
)

Coordinate = NDArray[np.float64]

# For a diagram, see
# https://ekiefl.github.io/2020/12/20/pooltool-alg/#ball-cushion-collision-times


@attrs.define(frozen=True)
class Jaw:
    """Jaw IDs for a pocket

    Left and right are defined relative to the shooter
    """

    left_edge: str
    left_rail: str
    right_edge: str
    right_rail: str
    corner: bool


pocket_jaw_map: Dict[str, Jaw] = {
    "lb": Jaw("1", "18", "2", "3", True),
    "lc": Jaw("4", "3", "5", "6", False),
    "lt": Jaw("7", "6", "8", "9", True),
    "rb": Jaw("16", "15", "17", "18", True),
    "rc": Jaw("13", "12", "14", "15", False),
    "rt": Jaw("10", "9", "11", "12", True),
}


def potting_point_side(_: Ball, table: Table, pocket: Pocket) -> Coordinate:
    jaw = pocket_jaw_map[pocket.id]
    lrail = table.cushion_segments.linear[jaw.left_rail]
    rrail = table.cushion_segments.linear[jaw.right_rail]

    # Unfortunately, we don't know which two endpoints of each cushion segment define the
    # jaws of the pocket, so we calculate distances between the two left points against
    # the two right points. The minimum distance are the pocket jaws, and for these two
    # points we calculate the "midpoint between jaws" (MBJ). That's our potting point.

    min_dist = np.inf
    MBJ = np.empty(2)
    for pl, pr in (
        (lrail.p1, rrail.p1),
        (lrail.p1, rrail.p2),
        (lrail.p2, rrail.p1),
        (lrail.p2, rrail.p2),
    ):
        dist = norm3d(pl - pr)
        if dist < min_dist:
            min_dist = dist
            MBJ = (pl + (pr - pl) / 2)[:2]

    return MBJ


def potting_point_corner(ball: Ball, table: Table, pocket: Pocket) -> Coordinate:
    jaw = pocket_jaw_map[pocket.id]
    lrail = table.cushion_segments.linear[jaw.left_rail]
    rrail = table.cushion_segments.linear[jaw.right_rail]

    # adjacent cushion intersection
    ACI = find_intersection_2D(
        l1x=lrail.lx,
        l1y=lrail.ly,
        l10=lrail.l0,
        l2x=rrail.lx,
        l2y=rrail.ly,
        l20=rrail.l0,
    )

    ball_to_ACI = ACI - ball.xyz[:2]

    lrail_unit = unit_vector(lrail.p2 - lrail.p1)[:2]
    rrail_unit = unit_vector(rrail.p2 - rrail.p1)[:2]

    # Point the cushion unit vectors towards the pocket
    if np.dot(ball_to_ACI, lrail_unit) < 0:
        lrail_unit *= -1
    if np.dot(ball_to_ACI, rrail_unit) < 0:
        rrail_unit *= -1

    theta_lrail = np.abs(angle_between_vectors(ball_to_ACI, lrail_unit))
    theta_rrail = np.abs(angle_between_vectors(ball_to_ACI, rrail_unit))

    assert theta_lrail <= 90.0
    assert theta_rrail <= 90.0

    # The rail with smallest theta is the rail ball is closest towards
    # Offset will be in opposite direction of other rail
    if theta_lrail < theta_rrail:
        theta = 45.0 - theta_lrail
        offset_dir = -rrail_unit
    else:
        theta = 45.0 - theta_rrail
        offset_dir = -lrail_unit

    assert 45.0 >= theta >= 0.0

    # Apply a linear interpolation, such that
    # theta = 0 -> 0
    # theta = 45 -> R
    offset_mag = theta / 45 * ball.params.R
    return ACI + offset_dir * offset_mag


def get_potting_point(ball: Ball, table: Table, pocket: Pocket) -> Coordinate:
    """The 2D coordinates that should be aimed at for the ball to be sunk"""
    return (
        potting_point_corner(ball, table, pocket)
        if pocket_jaw_map[pocket.id].corner
        else potting_point_side(ball, table, pocket)
    )


def calc_cut_angle(
    cueball: Coordinate, ball: Coordinate, potting_point: Coordinate
) -> float:
    aim_vector = ball[0] - cueball[0], ball[1] - cueball[1]
    pocket_vector = potting_point[0] - ball[0], potting_point[1] - ball[1]
    return angle_between_vectors(aim_vector, pocket_vector)


def calc_shadow_ball_center(ball: Ball, table: Table, pocket: Pocket) -> Coordinate:
    """Return coordinates of shadow ball for potting into specific pocket"""

    potting_point = get_potting_point(ball, table, pocket)

    # Calculate the unit vector drawn from the object ball to the pocket
    ball_to_pocket_vector = unit_vector_slow(potting_point - ball.xyz[:2])

    # The shadow ball center is two ball radii away from the object ball center
    magnitude = ball.params.R * 2

    # In the direction opposite the ball to pocket vector
    return ball.xyz[:2] - ball_to_pocket_vector * magnitude


def calc_potting_angle(
    cueball: Ball, ball: Ball, table: Table, pocket: Pocket
) -> float:
    """Return potting angle phi for potting into pocket"""
    p1 = cueball.xyz[:2]
    p2 = calc_shadow_ball_center(ball, table, pocket)

    (x1, y1), (x2, y2) = p1, p2
    x_diff, y_diff = x2 - x1, y2 - y1

    return math.degrees(math.atan2(y_diff, x_diff))


def pick_best_pot(
    cueball: Ball, ball: Ball, table: Table, pockets: Optional[Sequence[Pocket]] = None
) -> Pocket:
    """Return best pocket to pot ball into

    This function calculates the potting angle required for each pocket. The "best"
    pocket is the one where the pot requires the smallest cut angle.

    If pockets is not passed, all pockets on the table will be used.
    """

    _pockets: Sequence[Pocket] = (
        list(table.pockets.values()) if pockets is None else pockets
    )

    best_pocket, min_cut_angle = _pockets[0], 90.0
    for pocket in _pockets:
        potting_point = get_potting_point(ball, table, pocket)
        cut_angle = calc_cut_angle(
            cueball=cueball.xyz[:2],
            ball=calc_shadow_ball_center(ball, table, pocket),
            potting_point=potting_point,
        )
        if abs(cut_angle) < abs(min_cut_angle):  # Prefer a straighter shot
            min_cut_angle = cut_angle
            best_pocket = pocket

    return best_pocket
