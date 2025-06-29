"""Models for ball-cushion collisions."""

from typing import cast

import attrs

from pooltool.physics.resolve.ball_cushion.core import (
    BallCCushionCollisionStrategy,
    BallLCushionCollisionStrategy,
)
from pooltool.physics.resolve.ball_cushion.han_2005 import (
    Han2005Circular,
    Han2005Linear,
)
from pooltool.physics.resolve.ball_cushion.mathavan_2010 import (
    Mathavan2010Circular,
    Mathavan2010Linear,
)
from pooltool.physics.resolve.ball_cushion.unrealistic import (
    UnrealisticCircular,
    UnrealisticLinear,
)
from pooltool.physics.resolve.models import BallCCushionModel, BallLCushionModel

_ball_lcushion_model_registry: tuple[type[BallLCushionCollisionStrategy], ...] = (
    Mathavan2010Linear,
    Han2005Linear,
    UnrealisticLinear,
)

_ball_ccushion_model_registry: tuple[type[BallCCushionCollisionStrategy], ...] = (
    Mathavan2010Circular,
    Han2005Circular,
    UnrealisticCircular,
)

ball_lcushion_models: dict[BallLCushionModel, type[BallLCushionCollisionStrategy]] = {
    cast(BallLCushionModel, attrs.fields_dict(cls)["model"].default): cls
    for cls in _ball_lcushion_model_registry
}

ball_ccushion_models: dict[BallCCushionModel, type[BallCCushionCollisionStrategy]] = {
    cast(BallCCushionModel, attrs.fields_dict(cls)["model"].default): cls
    for cls in _ball_ccushion_model_registry
}
