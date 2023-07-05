from typing import Dict, Optional, Protocol, Tuple, Type

from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.table.components import (
    CircularCushionSegment,
    LinearCushionSegment,
)
from pooltool.physics.resolve.ball_cushion.han_2005 import (
    Han2005Circular,
    Han2005Linear,
)
from pooltool.physics.resolve.types import ModelArgs
from pooltool.utils.strenum import StrEnum, auto


class BallLCushionCollisionStrategy(Protocol):
    def resolve(
        self, ball: Ball, cushion: LinearCushionSegment, inplace: bool = False
    ) -> Tuple[Ball, LinearCushionSegment]:
        ...


class BallCCushionCollisionStrategy(Protocol):
    def resolve(
        self, ball: Ball, cushion: CircularCushionSegment, inplace: bool = False
    ) -> Tuple[Ball, CircularCushionSegment]:
        ...


class BallLCushionModel(StrEnum):
    HAN_2005 = auto()


class BallCCushionModel(StrEnum):
    HAN_2005 = auto()


_ball_lcushion_models: Dict[BallLCushionModel, Type[BallLCushionCollisionStrategy]] = {
    BallLCushionModel.HAN_2005: Han2005Linear,
}

_ball_ccushion_models: Dict[BallCCushionModel, Type[BallCCushionCollisionStrategy]] = {
    BallCCushionModel.HAN_2005: Han2005Circular,
}


BALL_LINEAR_CUSHION_DEFAULT = Han2005Linear()
BALL_CIRCULAR_CUSHION_DEFAULT = Han2005Circular()


def get_ball_lin_cushion_model(
    model: Optional[BallLCushionModel] = None, params: ModelArgs = {}
) -> BallLCushionCollisionStrategy:
    if model is None:
        return BALL_LINEAR_CUSHION_DEFAULT

    return _ball_lcushion_models[model](**params)


def get_ball_circ_cushion_model(
    model: Optional[BallCCushionModel] = None, params: ModelArgs = {}
) -> BallCCushionCollisionStrategy:
    if model is None:
        return BALL_CIRCULAR_CUSHION_DEFAULT

    return _ball_ccushion_models[model](**params)
