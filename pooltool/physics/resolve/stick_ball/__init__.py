from typing import Dict, Type

from pooltool.physics.resolve.models import StickBallModel
from pooltool.physics.resolve.stick_ball.core import StickBallCollisionStrategy
from pooltool.physics.resolve.stick_ball.instantaneous_point import InstantaneousPoint

stick_ball_models: Dict[StickBallModel, Type[StickBallCollisionStrategy]] = {
    StickBallModel.INSTANTANEOUS_POINT: InstantaneousPoint,
}
