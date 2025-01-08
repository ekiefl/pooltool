"""Physics subpackage for pooltool"""

from pooltool.physics import evolve, resolve
from pooltool.physics.engine import PhysicsEngine
from pooltool.physics.resolve.ball_ball import (
    BallBallCollisionStrategy,
    BallBallModel,
    ball_ball_models,
)
from pooltool.physics.resolve.ball_cushion import (
    BallCCushionCollisionStrategy,
    BallCCushionModel,
    BallLCushionCollisionStrategy,
    BallLCushionModel,
    ball_ccushion_models,
    ball_lcushion_models,
)
from pooltool.physics.resolve.ball_pocket import (
    BallPocketModel,
    BallPocketStrategy,
    ball_pocket_models,
)
from pooltool.physics.resolve.resolver import (
    RESOLVER_PATH,
    Resolver,
)
from pooltool.physics.resolve.stick_ball import (
    StickBallCollisionStrategy,
    StickBallModel,
    stick_ball_models,
)
from pooltool.physics.resolve.transition import (
    BallTransitionModel,
    BallTransitionStrategy,
    ball_transition_models,
)

__all__ = [
    "BallBallCollisionStrategy",
    "BallCCushionCollisionStrategy",
    "BallLCushionCollisionStrategy",
    "BallPocketStrategy",
    "StickBallCollisionStrategy",
    "BallTransitionStrategy",
    "PhysicsEngine",
    "evolve",
    "resolve",
    "Resolver",
    "RESOLVER_PATH",
    "BallBallModel",
    "BallCCushionModel",
    "BallLCushionModel",
    "BallPocketModel",
    "StickBallModel",
    "BallTransitionModel",
    "ball_ball_models",
    "ball_lcushion_models",
    "ball_ccushion_models",
    "ball_pocket_models",
    "stick_ball_models",
    "ball_transition_models",
]
