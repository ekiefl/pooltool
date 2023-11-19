"""A simple aiming procedure

The concept of this aiming procedure is to determine the cueing angle phi such that the
cue ball contacts the object ball on the aim line. Cut- and spin-induced throw is
ignored. Bank shots are not supported. Interfering balls are not detected.
"""

import math
from typing import Dict, Sequence

import attrs
import numpy as np
from numpy.typing import NDArray

from pooltool.objects import Ball, Pocket, Table
from pooltool.ptmath import angle_between_vectors, unit_vector_slow

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


def _potting_point_side(table: Table, pocket_id: str) -> Coordinate:
    pass


def _potting_point_corner(table: Table, pocket_id: str) -> Coordinate:
    pass


def potting_point(table: Table, pocket_id: str) -> Coordinate:
    """The 2D coordinates that should be aimed at for the ball to be sunk

    Determines the coordinates of a point ahead of the pocket where, if a traveling
    ball were to pass through it, would result in the ball being sunk. These values were
    determined by voodoo.
    """
    jaw = table.pockets[pocket_id]

    if jaw.corner:
        return _potting_point_corner(table, pocket_id)
    else:
        return _potting_point_side(table, pocket_id)

    (x, y, _), r = self.center, self.radius

    if self.id[0] == "l":
        x = x + r
    else:
        x = x - r

    if self.id[1] == "b":
        y = y + r
    elif self.id[1] == "t":
        y = y - r

    return np.array([x, y], dtype=np.float64)


def calc_cut_angle(
    cueball: Coordinate, ball: Coordinate, potting_point: Coordinate
) -> float:
    aim_vector = ball[0] - cueball[0], ball[1] - cueball[1]
    pocket_vector = potting_point[0] - ball[0], potting_point[1] - ball[1]
    return angle_between_vectors(aim_vector, pocket_vector)


def calc_shadow_ball_center(ball: Ball, pocket: Pocket) -> Coordinate:
    """Return coordinates of shadow ball for potting into specific pocket"""

    # Calculate the unit vector drawn from the object ball to the pocket
    ball_to_pocket_vector = unit_vector_slow(pocket.potting_point - ball.xyz[:2])

    # The shadow ball center is two ball radii away from the object ball center
    magnitude = ball.params.R * 2

    # In the direction opposite the ball to pocket vector
    return ball.xyz[:2] - ball_to_pocket_vector * magnitude


def calc_potting_angle(cueball: Ball, ball: Ball, pocket: Pocket) -> float:
    """Return potting angle phi for potting into pocket"""
    p1 = cueball.xyz[:2]
    p2 = calc_shadow_ball_center(ball, pocket)

    (x1, y1), (x2, y2) = p1, p2
    x_diff, y_diff = x2 - x1, y2 - y1

    return math.degrees(math.atan2(y_diff, x_diff))


def pick_best_pot(cueball: Ball, ball: Ball, pockets: Sequence[Pocket]) -> Pocket:
    """Return best pocket to pot ball into

    This function calculates the potting angle required for each pocket. The "best"
    pocket is the one where the pot requires the smallest cut angle.
    """

    best_pocket, min_cut_angle = pockets[0], 90.0
    for pocket in pockets:
        cut_angle = calc_cut_angle(
            cueball=cueball.xyz[:2],
            ball=calc_shadow_ball_center(ball, pocket),
            potting_point=pocket.potting_point,
        )
        if abs(cut_angle) < abs(min_cut_angle):  # Prefer a straighter shot
            min_cut_angle = cut_angle
            best_pocket = pocket

    return best_pocket
