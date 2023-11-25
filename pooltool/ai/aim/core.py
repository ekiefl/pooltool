from typing import overload

import numpy as np
from numpy.typing import NDArray

import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball
from pooltool.system.datatypes import System


@overload
def at_pos(system: System, pos: NDArray[np.float64]) -> float:
    ...


@overload
def at_pos(cue_ball: Ball, pos: NDArray[np.float64]) -> float:
    ...


def at_pos(*args) -> float:  # type: ignore
    """Return phi required to aim at specific 3D position"""
    assert len(args) == 2
    if isinstance(system := args[0], System):
        return _at_pos(system.balls[system.cue.cue_ball_id], args[1])
    elif isinstance(args[0], Ball):
        return _at_pos(*args)
    else:
        raise TypeError("Invalid arguments for at_pos")


def _at_pos(cue_ball: Ball, pos: NDArray[np.float64]) -> float:
    vector = ptmath.unit_vector(np.array(pos) - cue_ball.state.rvw[0])
    direction = ptmath.angle(vector)

    return direction * 180 / np.pi


@overload
def at_ball(system: System, ball_id: str, *, cut: float = 0.0) -> float:
    ...


@overload
def at_ball(cue_ball: Ball, object_ball: Ball, *, cut: float = 0.0) -> float:
    ...


def at_ball(*args, **kwargs) -> float:  # type: ignore
    """Returns phi to hit ball with specified cut angle (assumes straight line shot)"""
    if len(kwargs):
        assert len(kwargs) == 1
        assert "cut" in kwargs

    if isinstance(system := args[0], System) and isinstance(args[1], str):
        assert len(args) == 2
        cue_ball = system.balls[system.cue.cue_ball_id]
        object_ball = system.balls[args[1]]
        return _at_ball(cue_ball, object_ball, **kwargs)
    elif isinstance(args[0], Ball) and isinstance(args[1], Ball):
        assert len(args) == 2
        return _at_pos(*args, **kwargs)
    else:
        raise TypeError("Invalid arguments for at_ball")


def _at_ball(cue_ball: Ball, object_ball: Ball, cut: float = 0.0) -> float:
    phi = at_pos(cue_ball, object_ball.state.rvw[0])

    if cut == 0.0:
        return phi

    assert -89.0 <= cut <= 89.0, "Cut must be less than 89 and more than -89"

    left = True if cut < 0 else False
    cut = np.abs(cut) * np.pi / 180
    R = object_ball.params.R
    d = ptmath.norm3d(object_ball.state.rvw[0] - cue_ball.state.rvw[0])

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
