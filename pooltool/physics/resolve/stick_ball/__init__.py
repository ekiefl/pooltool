from typing import Dict, Tuple, Type, cast

import attrs

from pooltool.physics.resolve.models import StickBallModel
from pooltool.physics.resolve.stick_ball.core import StickBallCollisionStrategy
from pooltool.physics.resolve.stick_ball.instantaneous_point import InstantaneousPoint

_stick_ball_model_registry: Tuple[Type[StickBallCollisionStrategy], ...] = (
    InstantaneousPoint,
)

stick_ball_models: Dict[StickBallModel, Type[StickBallCollisionStrategy]] = {
    cast(StickBallModel, attrs.fields_dict(cls)["model"].default): cls
    for cls in _stick_ball_model_registry
}
