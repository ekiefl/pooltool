"""Physics subpackage for pooltool"""

from pooltool.physics import evolve, resolve
from pooltool.physics.engine import PhysicsEngine
from pooltool.physics.resolve.ball_ball import (
    BallBallCollisionStrategy,
    BallBallModel,
)
from pooltool.physics.resolve.ball_cushion import (
    BallCCushionCollisionStrategy,
    BallCCushionModel,
    BallLCushionCollisionStrategy,
    BallLCushionModel,
)
from pooltool.physics.resolve.ball_pocket import (
    BallPocketModel,
    BallPocketStrategy,
)
from pooltool.physics.resolve.resolver import (
    RESOLVER_PATH,
    Resolver,
)
from pooltool.physics.resolve.stick_ball import (
    StickBallCollisionStrategy,
    StickBallModel,
)
from pooltool.physics.resolve.transition import (
    BallTransitionModel,
    BallTransitionStrategy,
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
]
