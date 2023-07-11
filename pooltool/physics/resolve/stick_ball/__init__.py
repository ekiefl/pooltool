from typing import Dict, Optional, Type

from pooltool.physics.resolve.stick_ball.core import StickBallCollisionStrategy
from pooltool.physics.resolve.stick_ball.instantaneous_point import InstantaneousPoint
from pooltool.physics.resolve.types import ModelArgs
from pooltool.utils.strenum import StrEnum, auto


class StickBallModel(StrEnum):
    INSTANTANEOUS_POINT = auto()


_stick_ball_models: Dict[StickBallModel, Type[StickBallCollisionStrategy]] = {
    StickBallModel.INSTANTANEOUS_POINT: InstantaneousPoint,
}


def get_stick_ball_model(
    model: Optional[StickBallModel] = None, params: ModelArgs = {}
) -> StickBallCollisionStrategy:
    if model is None:
        return InstantaneousPoint(throttle_english=True)

    return _stick_ball_models[model](**params)
