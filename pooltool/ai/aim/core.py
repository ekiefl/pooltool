from functools import partial
from typing import overload

import numpy as np
from numpy.typing import NDArray

import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball
from pooltool.system.datatypes import System


@overload
def at_pos(system: System, pos: NDArray[np.float64]) -> float: ...


@overload
def at_pos(cue_ball: Ball, pos: NDArray[np.float64]) -> float: ...


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
def at_ball(system: System, ball_id: str, *, cut: float = 0.0) -> float: ...


@overload
def at_ball(cue_ball: Ball, object_ball: Ball, *, cut: float = 0.0) -> float: ...


def at_ball(*args, **kwargs) -> float:
    """Returns phi to hit ball with specified cut angle (assumes straight line shot)"""

    # Extract 'cut' from kwargs, defaulting to 0.0
    cut = kwargs.pop("cut", 0.0)

    # Initialize variables
    cue_ball = None
    object_ball = None
    system = None
    ball_id = None

    # Collect positional arguments
    positional_args = list(args)

    # Process keyword arguments
    cue_ball_kwarg = kwargs.pop("cue_ball", None)
    object_ball_kwarg = kwargs.pop("object_ball", None)
    system_kwarg = kwargs.pop("system", None)
    ball_id_kwarg = kwargs.pop("ball_id", None)

    # Assign positional arguments based on their types
    while positional_args:
        arg = positional_args.pop(0)
        if isinstance(arg, System):
            if system is not None:
                raise TypeError("Multiple 'system' arguments provided")
            system = arg
        elif isinstance(arg, Ball):
            if cue_ball is None:
                cue_ball = arg
            elif object_ball is None:
                object_ball = arg
            else:
                raise TypeError("Too many Ball instances provided")
        elif isinstance(arg, str):
            if ball_id is not None:
                raise TypeError("Multiple 'ball_id' arguments provided")
            ball_id = arg
        else:
            raise TypeError(
                f"Unexpected positional argument of type {type(arg).__name__}"
            )

    # Override with keyword arguments if provided
    cue_ball = cue_ball_kwarg if cue_ball_kwarg is not None else cue_ball
    object_ball = object_ball_kwarg if object_ball_kwarg is not None else object_ball
    system = system_kwarg if system_kwarg is not None else system
    ball_id = ball_id_kwarg if ball_id_kwarg is not None else ball_id

    # Validate combinations
    if system and ball_id:
        if cue_ball or object_ball:
            raise TypeError(
                "Provide either 'system' and 'ball_id', or 'cue_ball' and 'object_ball', not both"
            )
        cue_ball = system.balls[system.cue.cue_ball_id]
        object_ball = system.balls[ball_id]
    elif cue_ball and object_ball:
        pass  # Both are already set
    else:
        raise TypeError(
            "Invalid arguments: must provide 'cue_ball' and 'object_ball', or 'system' and 'ball_id'"
        )

    # Ensure no unexpected keyword arguments are left
    if kwargs:
        unexpected_args = ", ".join(kwargs.keys())
        raise TypeError(f"Unexpected keyword arguments: {unexpected_args}")

    # Validate types
    if not isinstance(cue_ball, Ball) or not isinstance(object_ball, Ball):
        raise TypeError("cue_ball and object_ball must be Ball instances")

    return _at_ball(cue_ball, object_ball, cut=cut)


def _at_ball(cue_ball: Ball, object_ball: Ball, cut: float = 0.0) -> float:
    phi = at_pos(cue_ball, object_ball.state.rvw[0])

    if cut == 0.0:
        return phi

    assert -89.0 <= cut <= 89.0, "Cut must be less than 89 and more than -89"

    left = True if cut < 0 else False
    cut = np.abs(cut) * np.pi / 180
    R = object_ball.params.R
    d = ptmath.norm3d(object_ball.state.rvw[0] - cue_ball.state.rvw[0])

    # If for some reason d < 2R, set d = 2R
    d = max(d, 2 * R)

    lower_bound = 0
    upper_bound = np.pi / 2 - np.arccos((2 * R) / d)

    transcendental = partial(_transcendental, cut=cut, R=R, d=d)
    dphi = ptmath.solve_transcendental(transcendental, lower_bound, upper_bound)

    phi = (phi + 180 / np.pi * (dphi if left else -dphi)) % 360
    return phi


def _transcendental(dphi: float, cut: float, R: float, d: float) -> float:
    a = 2 * R * np.sin(cut - dphi)
    b = d - 2 * R * np.cos(cut - dphi)
    return np.arctan(a / b) - dphi
