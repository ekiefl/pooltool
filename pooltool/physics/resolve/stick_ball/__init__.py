from typing import Dict, Optional, Type

from pooltool.physics.resolve.stick_ball.core import StickBallCollisionStrategy
from pooltool.physics.resolve.models import StickBallModel
from pooltool.physics.resolve.stick_ball.instantaneous_point import InstantaneousPoint
from pooltool.physics.resolve.types import ModelArgs

_stick_ball_models: Dict[StickBallModel, Type[StickBallCollisionStrategy]] = {
    StickBallModel.INSTANTANEOUS_POINT: InstantaneousPoint,
}


def get_stick_ball_model(
    model: Optional[StickBallModel] = None, params: ModelArgs = {}
) -> StickBallCollisionStrategy:
    """Returns a stick-ball collision model

    Args:
        model:
            An Enum specifying the desired model. If not passed,
            :class:`InstantaneousPoint` is passed with empty params.
        params:
            A mapping of parameters accepted by the model.

    Returns:
        An instantiated model that satisfies the :class:`StickBallCollisionStrategy`
        protocol.
    """
    if model is None:
        return InstantaneousPoint()

    return _stick_ball_models[model](**params)
