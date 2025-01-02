from typing import Dict, Type

from pooltool.physics.resolve.ball_cushion.core import (
    BallCCushionCollisionStrategy,
    BallLCushionCollisionStrategy,
)
from pooltool.physics.resolve.ball_cushion.han_2005 import (
    Han2005Circular,
    Han2005Linear,
)
from pooltool.physics.resolve.ball_cushion.unrealistic import (
    UnrealisticCircular,
    UnrealisticLinear,
)
from pooltool.physics.resolve.models import BallCCushionModel, BallLCushionModel

ball_lcushion_models: Dict[BallLCushionModel, Type[BallLCushionCollisionStrategy]] = {
    BallLCushionModel.HAN_2005: Han2005Linear,
    BallLCushionModel.UNREALISTIC: UnrealisticLinear,
}

ball_ccushion_models: Dict[BallCCushionModel, Type[BallCCushionCollisionStrategy]] = {
    BallCCushionModel.HAN_2005: Han2005Circular,
    BallCCushionModel.UNREALISTIC: UnrealisticCircular,
}

__all__ = [
    "ball_lcushion_models",
    "ball_ccushion_models",
]
