from typing import Dict, Optional, Type

from pooltool.physics.resolve.ball_ball.core import BallBallCollisionStrategy
from pooltool.physics.resolve.ball_ball.frictionless_elastic import FrictionlessElastic
from pooltool.physics.resolve.types import ModelArgs
from pooltool.utils.strenum import StrEnum, auto


class BallBallModel(StrEnum):
    FRICTIONLESS_ELASTIC = auto()


_ball_ball_models: Dict[BallBallModel, Type[BallBallCollisionStrategy]] = {
    BallBallModel.FRICTIONLESS_ELASTIC: FrictionlessElastic,
}


def get_ball_ball_model(
    model: Optional[BallBallModel] = None, params: ModelArgs = {}
) -> BallBallCollisionStrategy:
    if model is None:
        return FrictionlessElastic()

    return _ball_ball_models[model](**params)
