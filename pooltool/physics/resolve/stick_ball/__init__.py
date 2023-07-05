from typing import Dict, Optional, Protocol, Tuple, Type

from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.cue.datatypes import Cue
from pooltool.physics.resolve.stick_ball.instantaneous_point import InstantaneousPoint
from pooltool.utils.strenum import StrEnum, auto


class StickBallCollisionStrategy(Protocol):
    def resolve(self, cue: Cue, ball: Ball, inplace: bool = False) -> Tuple[Cue, Ball]:
        ...


class StickBallModel(StrEnum):
    INSTANTANEOUS_POINT = auto()


_stick_ball_models: Dict[StickBallModel, Type[StickBallCollisionStrategy]] = {
    StickBallModel.INSTANTANEOUS_POINT: InstantaneousPoint,
}

STICK_BALL_DEFAULT = InstantaneousPoint()


def get_stick_ball_model(
    model: Optional[StickBallModel] = None, **kwargs
) -> StickBallCollisionStrategy:
    if model is None:
        return STICK_BALL_DEFAULT

    return _stick_ball_models[model](**kwargs)
