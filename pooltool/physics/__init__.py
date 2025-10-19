"""Physics subpackage for pooltool"""

from pooltool.physics.engine import PhysicsEngine
from pooltool.physics.evolve import (
    evolve_ball_motion,
)
from pooltool.physics.resolve import display_models
from pooltool.physics.resolve.ball_ball import (
    BallBallModel,
    ball_ball_models,
)
from pooltool.physics.resolve.ball_ball.friction import (
    BallBallFrictionModel,
    ball_ball_friction_models,
)
from pooltool.physics.resolve.ball_cushion import (
    BallCCushionModel,
    BallLCushionModel,
    ball_ccushion_models,
    ball_lcushion_models,
)
from pooltool.physics.resolve.ball_pocket import (
    BallPocketModel,
    ball_pocket_models,
)
from pooltool.physics.resolve.resolver import (
    RESOLVER_PATH,
    Resolver,
)
from pooltool.physics.resolve.stick_ball import (
    StickBallModel,
    stick_ball_models,
)
from pooltool.physics.resolve.transition import (
    BallTransitionModel,
    ball_transition_models,
)

__all__ = [
    "PhysicsEngine",
    # Resolve
    "display_models",
    "Resolver",
    "RESOLVER_PATH",
    "BallBallModel",
    "BallCCushionModel",
    "BallLCushionModel",
    "BallPocketModel",
    "StickBallModel",
    "BallTransitionModel",
    "ball_ball_models",
    "BallBallFrictionModel",
    "ball_ball_friction_models",
    "ball_lcushion_models",
    "ball_ccushion_models",
    "ball_pocket_models",
    "stick_ball_models",
    "ball_transition_models",
    # Evolve
    "evolve_ball_motion",
]
