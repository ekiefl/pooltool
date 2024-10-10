from typing import Dict, Optional, Type

from pooltool.physics.resolve.ball_ball.core import BallBallCollisionStrategy
from pooltool.physics.resolve.ball_ball.frictionless_elastic import FrictionlessElastic
from pooltool.physics.resolve.ball_ball.frictional_mathavan import FrictionalMathavan
from pooltool.physics.resolve.types import ModelArgs
from pooltool.utils.strenum import StrEnum, auto


class BallBallModel(StrEnum):
    """An Enum for different ball-ball collision models

    Attributes:
        FRICTIONLESS_ELASTIC:
            Frictionless, instantaneous, elastic, equal mass collision
            (:class:`FrictionlessElastic`).
    """

    FRICTIONLESS_ELASTIC = auto()
    FRICTIONAL_MATHAVAN = auto()


_ball_ball_models: Dict[BallBallModel, Type[BallBallCollisionStrategy]] = {
    BallBallModel.FRICTIONLESS_ELASTIC: FrictionlessElastic,
    BallBallModel.FRICTIONAL_MATHAVAN: FrictionalMathavan,
}


def get_ball_ball_model(
    model: Optional[BallBallModel] = None, params: ModelArgs = {}
) -> BallBallCollisionStrategy:
    """Returns a ball-ball collision model

    Args:
        model:
            An Enum specifying the desired model. If not passed,
            :class:`FrictionlessElastic` is passed with empty params.
        params:
            A mapping of parameters accepted by the model.

    Returns:
        An instantiated model that satisfies the :class:`BallBallCollisionStrategy`
        protocol.
    """

    if model is None:
        return FrictionlessElastic()

    return _ball_ball_models[model](**params)
