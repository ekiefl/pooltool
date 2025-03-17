"""Models for ball-cushion collisions."""

from typing import Dict, Tuple, Type, cast

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

_ball_lcushion_model_registry: Tuple[Type[BallLCushionCollisionStrategy], ...] = (
    Mathavan2010Linear,
    Han2005Linear,
    UnrealisticLinear,
)

_ball_ccushion_model_registry: Tuple[Type[BallCCushionCollisionStrategy], ...] = (
    Mathavan2010Circular,
    Han2005Circular,
    UnrealisticCircular,
)

ball_lcushion_models: Dict[BallLCushionModel, Type[BallLCushionCollisionStrategy]] = {
    cast(BallLCushionModel, attrs.fields_dict(cls)["model"].default): cls
    for cls in _ball_lcushion_model_registry
}

ball_ccushion_models: Dict[BallCCushionModel, Type[BallCCushionCollisionStrategy]] = {
    cast(BallCCushionModel, attrs.fields_dict(cls)["model"].default): cls
    for cls in _ball_ccushion_model_registry
}


__all__ = [
    "ball_lcushion_models",
    "ball_ccushion_models",
    "Mathavan2010Linear",
    "Han2005Linear",
    "UnrealisticLinear",
    "Mathavan2010Circular",
    "Han2005Circular",
    "UnrealisticCircular",
    "BallCCushionModel",
    "BallLCushionModel",
]
