"""A simple aiming procedure

The concept of this aiming procedure is to determine the cueing angle phi such that the
cue ball contacts the object ball on the aim line. Cut- and spin-induced throw is
ignored. Bank shots are not supported. Interfering balls are not detected.
"""

import math
from typing import Sequence

import numpy as np
from numpy.typing import NDArray

from pooltool.objects import Ball, Pocket
from pooltool.utils import unit_vector


def angle_between_points(p1, p2) -> float:
    (x1, y1), (x2, y2) = p1, p2
    x_diff, y_diff = x2 - x1, y2 - y1
    return math.degrees(math.atan2(y_diff, x_diff))


def angle_between_vectors(v1, v2) -> float:
    angle = np.math.atan2(np.linalg.det([v1, v2]), np.dot(v1, v2))  # type: ignore
    return math.degrees(angle)


def calc_cut_angle(c, b, p) -> float:
    aim_vector = b[0] - c[0], b[1] - c[1]
    pocket_vector = p[0] - b[0], p[1] - b[1]
    return angle_between_vectors(aim_vector, pocket_vector)


def calc_shadow_ball_center(ball: Ball, pocket: Pocket) -> NDArray:
    """Return coordinates of shadow ball for potting into specific pocket"""

    # Calculate the unit vector drawn from the object ball to the pocket
    ball_to_pocket_vector = unit_vector(pocket.potting_point - ball.xyz[:2])

    # The shadow ball center is two ball radii away from the object ball center
    magnitude = ball.params.R * 2

    # In the direction opposite the ball to pocket vector
    return ball.xyz[:2] - ball_to_pocket_vector * magnitude


def calc_potting_angle(cue_ball: Ball, object_ball: Ball, pocket: Pocket) -> float:
    """Return potting angle phi for potting into pocket"""
    return angle_between_points(
        cue_ball.xyz[:2], calc_shadow_ball_center(object_ball, pocket)
    )


def pick_best_pot(
    cue_ball: Ball, object_ball: Ball, pockets: Sequence[Pocket]
) -> Pocket:
    """Return best pocket to pot ball into

    This function calculates the potting angle required for each pocket. The "best"
    pocket is the one where the pot requires the smallest cut angle.
    """

    best_pocket, min_cut_angle = pockets[0], 90.0
    for pocket in pockets:
        cut_angle = calc_cut_angle(
            c=cue_ball.xyz[:2],
            b=calc_shadow_ball_center(object_ball, pocket),
            p=pocket.potting_point,
        )
        if abs(cut_angle) < abs(min_cut_angle):  # Prefer a straighter shot
            min_cut_angle = cut_angle
            best_pocket = pocket

    return best_pocket
