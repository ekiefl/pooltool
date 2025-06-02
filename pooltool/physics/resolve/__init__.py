"""Resolve events"""

import inspect

import attrs

from pooltool.physics.resolve.ball_ball import (
    BallBallModel,
    ball_ball_models,
)
from pooltool.physics.resolve.ball_cushion import (
    BallCCushionModel,
    BallLCushionModel,
    ball_ccushion_models,
    ball_lcushion_models,
)
from pooltool.physics.resolve.ball_pocket import (
    BallPocketModel,
    ball_pocket_models,
)
from pooltool.physics.resolve.resolver import (
    RESOLVER_PATH,
    Resolver,
)
from pooltool.physics.resolve.stick_ball import (
    StickBallModel,
    stick_ball_models,
)
from pooltool.physics.resolve.transition import (
    BallTransitionModel,
    ball_transition_models,
)


def _display_model(cls, model):
    fp = inspect.getfile(cls)
    print(f"  {model.value} ({fp})")

    if not attrs.has(cls):
        raise TypeError(f"{cls.__name__} is not an attrs class.")

    indent = 4
    indent_str = " " * indent

    for field in attrs.fields(cls):
        if field.name == "model":
            continue

        default_val = field.default
        if default_val is attrs.NOTHING:
            default_val = None

        print(f"{indent_str}  - {field.name}: type={field.type}, default={default_val}")


def display_models():
    print("\nball_ball models:")
    for model in BallBallModel:
        _display_model(ball_ball_models[model], model)
    print("\nball_linear_cushion models:")
    for model in BallLCushionModel:
        _display_model(ball_lcushion_models[model], model)
    print("\nball_circular_cushion models:")
    for model in BallCCushionModel:
        _display_model(ball_ccushion_models[model], model)
    print("\nstick_ball models:")
    for model in StickBallModel:
        _display_model(stick_ball_models[model], model)
    print("\nball_pocket models:")
    for model in BallPocketModel:
        _display_model(ball_pocket_models[model], model)
    print("\nball_transition models:")
    for model in BallTransitionModel:
        _display_model(ball_transition_models[model], model)


__all__ = [
    "Resolver",
    "RESOLVER_PATH",
]
