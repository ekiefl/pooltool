"""A simple aiming procedure

The concept of this aiming procedure is to determine the cueing angle phi such that the
cue ball contacts the object ball on the aim line. Cut- and spin-induced throw is
ignored. Bank shots are not supported. Interfering balls are not detected.
"""

import math
from typing import Dict, Iterable, List, Optional, Set, Tuple

import attrs
import numpy as np
from numpy.typing import NDArray

import pooltool.constants as const
from pooltool.objects import Ball, BallState, Pocket, Table
from pooltool.ptmath import (
    angle_between_vectors,
    are_points_on_same_side,
    find_intersection_2D,
    norm2d,
    norm3d,
    point_on_line_closest_to_point,
    unit_vector,
    unit_vector_slow,
)
from pooltool.system.datatypes import System

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
    left_tip: str
    right_edge: str
    right_rail: str
    right_tip: str
    corner: bool


pocket_jaw_map: Dict[str, Jaw] = {
    "lb": Jaw("1", "18", "1t", "2", "3", "2t", True),
    "lc": Jaw("4", "3", "4t", "5", "6", "5t", False),
    "lt": Jaw("7", "6", "7t", "8", "9", "8t", True),
    "rb": Jaw("16", "15", "16t", "17", "18", "17t", True),
    "rc": Jaw("13", "12", "13t", "14", "15", "14t", False),
    "rt": Jaw("10", "9", "10t", "11", "12", "11t", True),
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
    # Treatment varies if ball is considered "in the jaws of the pocket"
    potting_point = potting_point_jaw_treatment(ball, table, pocket)
    if potting_point is not None:
        return potting_point

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
    offset_mag = np.sin(np.pi / 90 * theta) * ball.params.R
    return ACI + offset_dir * offset_mag


def potting_point_jaw_treatment(
    ball: Ball, table: Table, pocket: Pocket
) -> Optional[Coordinate]:
    """Determines if ball is in jaws of pocket, decides what to do if should

    Returns:
        If None, the ball is not considered in the jaws of the pocket.
    """

    jaw = pocket_jaw_map[pocket.id]
    lrail = table.cushion_segments.linear[jaw.left_rail]
    ledge = table.cushion_segments.linear[jaw.left_edge]
    rrail = table.cushion_segments.linear[jaw.right_rail]
    redge = table.cushion_segments.linear[jaw.right_edge]

    # Find intersection of edge and rail for left and right
    lpoint = find_intersection_2D(
        l1x=lrail.lx,
        l1y=lrail.ly,
        l10=lrail.l0,
        l2x=ledge.lx,
        l2y=ledge.ly,
        l20=ledge.l0,
    )
    rpoint = find_intersection_2D(
        l1x=rrail.lx,
        l1y=rrail.ly,
        l10=rrail.l0,
        l2x=redge.lx,
        l2y=redge.ly,
        l20=redge.l0,
    )

    # Consider the line between lpoint and rpoint. Is the center of object ball on the
    # same side of this line as the pocket center? If so, it's considered in the jaws
    in_jaws = are_points_on_same_side(lpoint, rpoint, ball.xyz, pocket.center)

    return pocket.center[:2] if in_jaws else None


def get_potting_point(ball: Ball, table: Table, pocket: Pocket) -> Coordinate:
    """The 2D coordinates that should be aimed at for the ball to be sunk"""
    return (
        potting_point_corner(ball, table, pocket)
        if pocket_jaw_map[pocket.id].corner
        else potting_point_side(ball, table, pocket)
    )


def calc_cut_angle(
    cueball: Coordinate, ghost_ball: Coordinate, potting_point: Coordinate
) -> float:
    aim_vector = ghost_ball[0] - cueball[0], ghost_ball[1] - cueball[1]
    pocket_vector = potting_point[0] - ghost_ball[0], potting_point[1] - ghost_ball[1]
    return angle_between_vectors(np.array(aim_vector), np.array(pocket_vector))


def ball_ids_occluding_ballpath(
    ball: Ball, aim_spot: Coordinate, balls: Iterable[Ball]
) -> Set[str]:
    """Returns IDs of balls that occlude the straight line ball path from p1 to p2

    Assumes the ball taking the ball path has radius R
    """

    p1 = ball.xyz[:2]
    p2 = aim_spot

    occluding_ball_ids = set()
    for _ball in balls:
        if ball.id == _ball.id:
            continue

        if ball.state.s == const.pocketed:
            continue

        p0 = _ball.xyz[:2]

        closest = point_on_line_closest_to_point(p1, p2, p0)
        s_score = -np.dot(p1 - closest, p2 - p1) / np.dot(p2 - p1, p2 - p1)
        if s_score < 0 or s_score > 1:
            continue

        distance = norm2d(closest - p0)
        if distance < 2 * _ball.params.R:
            occluding_ball_ids.add(_ball.id)

    return occluding_ball_ids


def is_object_ball_occluded(
    cue: Ball, ball: Ball, table: Table, pocket: Pocket, balls: Iterable[Ball]
) -> bool:
    """Is the cue's path to the object ball occluded?"""
    aim_spot = calc_shadow_ball_center(ball, table, pocket)

    occluding_ids = ball_ids_occluding_ballpath(cue, aim_spot, balls)
    occluding_ids.discard(cue.id)
    occluding_ids.discard(ball.id)

    return bool(len(occluding_ids))


def is_pocket_occluded(
    ball: Ball, table: Table, pocket: Pocket, balls: Iterable[Ball]
) -> bool:
    """Is the object ball's path to the potting point occluded?"""
    aim_spot = get_potting_point(ball, table, pocket)

    occluding_ids = ball_ids_occluding_ballpath(ball, aim_spot, balls)
    occluding_ids.discard(ball.id)

    return bool(len(occluding_ids))


def is_room_for_cue_ball(
    ball: Ball, table: Table, pocket: Pocket, balls: Iterable[Ball]
) -> bool:
    R = ball.params.R
    shadow_ball_coords = calc_shadow_ball_center(ball, table, pocket)

    if (
        shadow_ball_coords[0] < R
        or shadow_ball_coords[0] > table.w - R
        or shadow_ball_coords[1] < R
        or shadow_ball_coords[1] > table.l - R
    ):
        return False

    for _ball in balls:
        if ball.id == _ball.id:
            continue

        if norm2d(_ball.xyz[:2] - shadow_ball_coords) < 2 * _ball.params.R:
            return False

    return True


def is_jaw_in_way(ball: Ball, table: Table, pocket: Pocket) -> bool:
    """Is the the closest jaw in the way of the potting point?

    When shooting into the side pocket, there is often not enough pocket to aim at, in
    particular when the object ball is close to the rail that the pocket is on. One way
    of imagining the problem is that the closest jaw "gets in the way" of the object
    ball shot path.

    This function calculates whether or not the close jaw is in the way of the shot path
    by determining the point on the shot path that is closest to the jaw tip center.
    (The jaw tip is a small circular cushion segment, used to round out the
    cushion tip). If the distance between this point and the jaw tip center is less than
    the jaw tip radius plus the ball radius, then the object ball would hit the close
    cushion, in which case this function returns True.
    """
    if pocket_jaw_map[pocket.id].corner:
        # Only side pockets have this problem
        return False

    jaw = pocket_jaw_map[pocket.id]
    ljaw_tip = table.cushion_segments.circular[jaw.left_tip]
    rjaw_tip = table.cushion_segments.circular[jaw.right_tip]

    # We consider the jaw tip closest to the ball
    jaw_tip = (
        ljaw_tip
        if norm3d(ljaw_tip.center - ball.xyz) < norm3d(rjaw_tip.center - ball.xyz)
        else rjaw_tip
    )

    closest_point_to_jaw = point_on_line_closest_to_point(
        ball.xyz[:2], get_potting_point(ball, table, pocket), jaw_tip.center[:2]
    )
    return (
        norm2d(closest_point_to_jaw - jaw_tip.center[:2])
        < jaw_tip.radius + ball.params.R
    )


def open_pockets(ball: Ball, table: Table, balls: Iterable[Ball]) -> Set[str]:
    """Return the IDs of pockets that are open to the ball

    An open pocket means that the ball has an unobscured path to the pocket, and that
    there is room to place a cue ball behind the object ball.

    See also: viable_pockets
    """
    return set(
        pocket.id
        for pocket in table.pockets.values()
        if not is_pocket_occluded(ball, table, pocket, balls)
        and is_room_for_cue_ball(ball, table, pocket, balls)
        and not is_jaw_in_way(ball, table, pocket)
    )


def required_precision(
    cue_state: BallState,
    ball_state: BallState,
    table: Table,
    pocket: Pocket,
) -> float:
    """Return the required precision for a pot

    This is not an exact calculation. What is returned is the difference in phi values
    required to aim the center of the object ball towards both jaw tips. So the returned
    value is exactly the variance in phi, within which you will still pot the ball. But,
    it _is_ still a proxy for how difficult the pot is.
    """
    jaw = pocket_jaw_map[pocket.id]
    lrail = table.cushion_segments.linear[jaw.left_rail]
    ledge = table.cushion_segments.linear[jaw.left_edge]
    rrail = table.cushion_segments.linear[jaw.right_rail]
    redge = table.cushion_segments.linear[jaw.right_edge]

    ltip = find_intersection_2D(
        l1x=lrail.lx,
        l1y=lrail.ly,
        l10=lrail.l0,
        l2x=ledge.lx,
        l2y=ledge.ly,
        l20=ledge.l0,
    )
    rtip = find_intersection_2D(
        l1x=rrail.lx,
        l1y=rrail.ly,
        l10=rrail.l0,
        l2x=redge.lx,
        l2y=redge.ly,
        l20=redge.l0,
    )

    phi_left = np.abs(
        calc_cut_angle(
            cue_state.rvw[0][:2],
            ball_state.rvw[0][:2],
            np.array([*ltip]),
        )
    )

    phi_right = np.abs(
        calc_cut_angle(
            cue_state.rvw[0][:2],
            ball_state.rvw[0][:2],
            np.array([*rtip]),
        )
    )

    # FIXME this is tolerance
    return np.abs(phi_left - phi_right)


def viable_pockets(
    cue: Ball,
    ball: Ball,
    table: Table,
    balls: Iterable[Ball],
    max_cut: float = 80,
) -> List[Tuple[str, float]]:
    """Return viable pockets that the cue ball can sink the object ball into

    A viable pocket is one that is:

        (1) Open
        (2) Max cut angle doesn't exceed max_cut. The theoretical max is 90
        (3) A straight line can be drawn between where the cue ball is and
            where the cue ball has to contact the object ball, without any
            obscuring balls or cushions.

    Returns:
        list of (pocket_id, required_precision), ordered with lowest precision first

    See also: open_pockets
    """

    viable = []
    for pocket in table.pockets.values():
        cut_angle = np.abs(
            calc_cut_angle(
                cue.xyz[:2],
                ball.xyz[:2],
                get_potting_point(ball, table, pocket),
            )
        )

        if (
            not is_pocket_occluded(ball, table, pocket, balls)
            and is_room_for_cue_ball(ball, table, pocket, balls)
            and not is_jaw_in_way(ball, table, pocket)
            and not is_object_ball_occluded(cue, ball, table, pocket, balls)
            and cut_angle <= max_cut
        ):
            viable.append(
                (pocket.id, required_precision(cue.state, ball.state, table, pocket))
            )

    return sorted(viable, key=lambda x: x[1])


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


def pick_easiest_pot(
    system: System,
    ball: Ball,
) -> Optional[Pocket]:
    """Return best pocket to pot ball into

    This function calculates the potting angle required, and the precision required, for
    each pocket. The "best" pocket is the one where the pot requires the smallest cut
    angle.
    """

    cue_ball = system.balls[system.cue.cue_ball_id]
    pocket_options = viable_pockets(
        cue_ball, ball, system.table, list(system.balls.values())
    )

    if not len(pocket_options):
        return None

    return system.table.pockets[pocket_options[0][0]]
