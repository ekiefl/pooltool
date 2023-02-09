"""A simple aiming procedure

The concept of this aiming procedure is to determine the cueing angle phi such that the
cue ball contacts the object ball on the aim line. Cut- and spin-induced throw is
ignored. Bank shots are not supported. Interfering balls are not detected.
"""

import math

import numpy as np


def line_equation(p1, p2):
    (x1, y1), (x2, y2) = p1, p2
    m = (y2 - y1) / (x2 - x1)
    b = y1 - m * x1
    return m, b


def calc_aiming_point(m, b, ball_center, pocket, d):
    # calculate the angle between x-axis and the line
    theta = math.atan(m)

    # calculate x and y coordinate of the point
    x0, y0 = ball_center
    # If the pocket is on the left, add to x0, else subtract
    sign = 1 if pocket.id[0] == "l" else -1
    aim_p_x = x0 + sign * d * math.cos(theta)
    aim_p_y = m * aim_p_x + b
    return aim_p_x, aim_p_y


def angle_between_points(p1, p2):
    (x1, y1), (x2, y2) = p1, p2
    x_diff, y_diff = x2 - x1, y2 - y1
    return math.degrees(math.atan2(y_diff, x_diff))


def angle_between_vectors(v1, v2):
    angle = np.math.atan2(np.linalg.det([v1, v2]), np.dot(v1, v2))
    return math.degrees(angle)


def calc_cut_angle(c, b, p):
    aim_vector = b[0] - c[0], b[1] - c[1]
    pocket_vector = p[0] - b[0], p[1] - b[1]
    return angle_between_vectors(aim_vector, pocket_vector)


def calc_potting_angle(cue, ball, pockets):
    """Return the cue phi angle required to pot the ball"""
    aim_point, min_cut_angle = None, 90
    for pocket in pockets:
        m, b = line_equation(ball.center, pocket.potting_point)
        shadow_ball_point = calc_aiming_point(m, b, ball.center, pocket, 2 * ball.R)
        cut_angle = calc_cut_angle(
            cue.cueing_ball.center, shadow_ball_point, pocket.potting_point
        )
        if abs(cut_angle) < abs(min_cut_angle):  # Prefer a straighter shot
            min_cut_angle = cut_angle
            aim_point = shadow_ball_point

    return (
        180
        if aim_point is None
        else angle_between_points(cue.cueing_ball.center, aim_point)
    )
