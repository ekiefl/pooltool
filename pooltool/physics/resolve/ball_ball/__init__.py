"""Models for ball-ball collisions."""

from typing import Dict, Type

from pooltool.physics.resolve.ball_ball.core import BallBallCollisionStrategy
from pooltool.physics.resolve.ball_ball.frictional_inelastic import FrictionalInelastic
from pooltool.physics.resolve.ball_ball.frictional_mathavan import FrictionalMathavan
from pooltool.physics.resolve.ball_ball.frictionless_elastic import FrictionlessElastic
from pooltool.physics.resolve.models import BallBallModel

ball_ball_models: Dict[BallBallModel, Type[BallBallCollisionStrategy]] = {
    BallBallModel.FRICTIONLESS_ELASTIC: FrictionlessElastic,
    BallBallModel.FRICTIONAL_INELASTIC: FrictionalInelastic,
    BallBallModel.FRICTIONAL_MATHAVAN: FrictionalMathavan,
}


__all__ = [
    "BallBallModel",
    "FrictionalMathavan",
    "FrictionalInelastic",
    "FrictionlessElastic",
    "ball_ball_models",
]
