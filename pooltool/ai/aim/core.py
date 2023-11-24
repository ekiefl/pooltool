import numpy as np
from numpy.typing import NDArray

import pooltool.ptmath as ptmath
from pooltool.error import ConfigError
from pooltool.system.datatypes import System


def at_pos(system: System, pos: NDArray[np.float64]) -> float:
    """Returns phi required for a straight line shot to a 3D position

    Args:
        pos:
            A length-3 iterable specifying the x, y, z coordinates of the position to be
            aimed at
    """

    assert system.cue.cue_ball_id in system.balls

    cueing_ball = system.balls[system.cue.cue_ball_id]

    vector = ptmath.unit_vector(np.array(pos) - cueing_ball.state.rvw[0])
    direction = ptmath.angle(vector)

    return direction * 180 / np.pi


def at_ball(system: System, ball_id: str, cut: float = 0.0) -> float:
    """Returns phi to hit a ball with specified cut angle (assumes straight line shot)

    Args:
        ball:
            A ball
        cut:
            The cut angle in degrees, within [-89, 89]. Negative is cutting the left
            side of the ball from the shooter's perspective.
    """

    assert system.cue.cue_ball_id in system.balls

    cueing_ball = system.balls[system.cue.cue_ball_id]
    object_ball = system.balls[ball_id]

    phi = at_pos(system, object_ball.state.rvw[0])

    if cut == 0.0:
        return phi

    assert -89.0 <= cut <= 89.0, "Cut must be less than 89 and more than -89"

    left = True if cut < 0 else False
    cut = np.abs(cut) * np.pi / 180
    R = object_ball.params.R
    d = ptmath.norm3d(object_ball.state.rvw[0] - cueing_ball.state.rvw[0])

    lower_bound = 0
    upper_bound = np.pi / 2 - np.arccos((2 * R) / d)

    transcendental = (
        lambda dphi: np.arctan(
            2 * R * np.sin(cut - dphi) / (d - 2 * R * np.cos(cut - dphi))
        )
        - dphi
    )
    dphi = ptmath.solve_transcendental_equation(
        transcendental, lower_bound, upper_bound
    )
    phi = (phi + 180 / np.pi * (dphi if left else -dphi)) % 360
    return phi
