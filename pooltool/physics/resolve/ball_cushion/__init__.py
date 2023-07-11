from typing import Dict, Optional, Type

from pooltool.physics.resolve.ball_cushion.core import (
    BallCCushionCollisionStrategy,
    BallLCushionCollisionStrategy,
)
from pooltool.physics.resolve.ball_cushion.han_2005 import (
    Han2005Circular,
    Han2005Linear,
)
from pooltool.physics.resolve.ball_cushion.unrealistic import UnrealisticLinear
from pooltool.physics.resolve.types import ModelArgs
from pooltool.utils.strenum import StrEnum, auto


class BallLCushionModel(StrEnum):
    HAN_2005 = auto()
    UNREALISTIC = auto()


class BallCCushionModel(StrEnum):
    HAN_2005 = auto()


_ball_lcushion_models: Dict[BallLCushionModel, Type[BallLCushionCollisionStrategy]] = {
    BallLCushionModel.HAN_2005: Han2005Linear,
    BallLCushionModel.UNREALISTIC: UnrealisticLinear,
}

_ball_ccushion_models: Dict[BallCCushionModel, Type[BallCCushionCollisionStrategy]] = {
    BallCCushionModel.HAN_2005: Han2005Circular,
}


def get_ball_lin_cushion_model(
    model: Optional[BallLCushionModel] = None, params: ModelArgs = {}
) -> BallLCushionCollisionStrategy:
    if model is None:
        return Han2005Linear()

    return _ball_lcushion_models[model](**params)


def get_ball_circ_cushion_model(
    model: Optional[BallCCushionModel] = None, params: ModelArgs = {}
) -> BallCCushionCollisionStrategy:
    if model is None:
        return Han2005Circular()

    return _ball_ccushion_models[model](**params)
