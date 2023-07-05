from typing import Dict, Optional, Protocol, Tuple, Type

from pooltool.objects.ball.datatypes import Ball
from pooltool.physics.resolve.ball_ball.frictionless_elastic import FrictionlessElastic
from pooltool.physics.resolve.types import ModelArgs
from pooltool.utils.strenum import StrEnum, auto


class BallBallCollisionStrategy(Protocol):
    def resolve(
        self, ball1: Ball, ball2: Ball, inplace: bool = False
    ) -> Tuple[Ball, Ball]:
        ...


class BallBallModel(StrEnum):
    FRICTIONLESS_ELASTIC = auto()


_ball_ball_models: Dict[BallBallModel, Type[BallBallCollisionStrategy]] = {
    BallBallModel.FRICTIONLESS_ELASTIC: FrictionlessElastic,
}


BALL_BALL_DEFAULT = FrictionlessElastic()


def get_ball_ball_model(
    model: Optional[BallBallModel] = None, params: ModelArgs = {}
) -> BallBallCollisionStrategy:
    if model is None:
        return BALL_BALL_DEFAULT

    return _ball_ball_models[model](**params)
