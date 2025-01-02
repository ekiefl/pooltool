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
from pooltool.physics.resolve.models import BallCCushionModel, BallLCushionModel
from pooltool.physics.resolve.types import ModelArgs

ball_lcushion_models: Dict[BallLCushionModel, Type[BallLCushionCollisionStrategy]] = {
    BallLCushionModel.HAN_2005: Han2005Linear,
    BallLCushionModel.UNREALISTIC: UnrealisticLinear,
}

ball_ccushion_models: Dict[BallCCushionModel, Type[BallCCushionCollisionStrategy]] = {
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

    return ball_lcushion_models[model](**params)


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

    return ball_ccushion_models[model](**params)
