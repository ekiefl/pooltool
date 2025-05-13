"""Models for ball-ball collisions."""

from typing import Dict, Tuple, Type, cast

import attrs

from pooltool.physics.resolve.ball_ball.core import BallBallCollisionStrategy
from pooltool.physics.resolve.ball_ball.frictional_inelastic import FrictionalInelastic
from pooltool.physics.resolve.ball_ball.frictional_mathavan import FrictionalMathavan
from pooltool.physics.resolve.ball_ball.frictionless_elastic import FrictionlessElastic
from pooltool.physics.resolve.models import BallBallModel

_ball_ball_model_registry: Tuple[Type[BallBallCollisionStrategy], ...] = (
    FrictionlessElastic,
    FrictionalMathavan,
    FrictionalInelastic,
)

ball_ball_models: Dict[BallBallModel, Type[BallBallCollisionStrategy]] = {
    cast(BallBallModel, attrs.fields_dict(cls)["model"].default): cls
    for cls in _ball_ball_model_registry
}
