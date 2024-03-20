from typing import Dict, Optional, Type

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
from pooltool.physics.resolve.types import ModelArgs
from pooltool.utils.strenum import StrEnum, auto


class BallLCushionModel(StrEnum):
    """An Enum for different ball-linear cushion collision models

    Attributes:
        HAN_2005:
            https://ekiefl.github.io/2020/04/24/pooltool-theory/#3-han-2005
            (:class:`Han2005Linear`).
        UNREALISTIC:
            An unrealistic model in which balls are perfectly reflected. Spin is left
            untouched by the interaction (:class:`UnrealisticLinear`).
    """

    HAN_2005 = auto()
    UNREALISTIC = auto()


class BallCCushionModel(StrEnum):
    """An Enum for different ball-circular cushion collision models

    Attributes:
        HAN_2005:
            https://ekiefl.github.io/2020/04/24/pooltool-theory/#3-han-2005
            (:class:`Han2005Linear`).
        UNREALISTIC:
            An unrealistic model in which balls are perfectly reflected. Spin is left
            untouched by the interaction (:class:`UnrealisticCircular`).
    """

    HAN_2005 = auto()
    UNREALISTIC = auto()


_ball_lcushion_models: Dict[BallLCushionModel, Type[BallLCushionCollisionStrategy]] = {
    BallLCushionModel.HAN_2005: Han2005Linear,
    BallLCushionModel.UNREALISTIC: UnrealisticLinear,
}

_ball_ccushion_models: Dict[BallCCushionModel, Type[BallCCushionCollisionStrategy]] = {
    BallCCushionModel.HAN_2005: Han2005Circular,
    BallCCushionModel.UNREALISTIC: UnrealisticCircular,
}


def get_ball_lin_cushion_model(
    model: Optional[BallLCushionModel] = None, params: ModelArgs = {}
) -> BallLCushionCollisionStrategy:
    """Returns a ball-linear cushion collision model

    Args:
        model:
            An Enum specifying the desired model. If not passed,
            :class:`Han2005Linear` is passed with empty params.
        params:
            A mapping of parameters accepted by the model.

    Returns:
        An instantiated model that satisfies the :class:`BallLCushionCollisionStrategy`
        protocol.
    """
    if model is None:
        return Han2005Linear()

    return _ball_lcushion_models[model](**params)


def get_ball_circ_cushion_model(
    model: Optional[BallCCushionModel] = None, params: ModelArgs = {}
) -> BallCCushionCollisionStrategy:
    """Returns a ball-circular cushion collision model

    Args:
        model:
            An Enum specifying the desired model. If not passed,
            :class:`Han2005Circular` is passed with empty params.
        params:
            A mapping of parameters accepted by the model.

    Returns:
        An instantiated model that satisfies the :class:`BallCCushionCollisionStrategy`
        protocol.
    """
    if model is None:
        return Han2005Circular()

    return _ball_ccushion_models[model](**params)
