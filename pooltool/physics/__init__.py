"""Physics subpackage for pooltool"""

from pooltool.physics import evolve, resolve
from pooltool.physics.engine import PhysicsEngine
from pooltool.physics.resolve.ball_ball import (
    BallBallModel,
    get_ball_ball_model,
)
from pooltool.physics.resolve.ball_cushion import (
    BallCCushionModel,
    BallLCushionModel,
    get_ball_circ_cushion_model,
    get_ball_lin_cushion_model,
)
from pooltool.physics.resolve.ball_pocket import (
    BallPocketModel,
    get_ball_pocket_model,
)
from pooltool.physics.resolve.resolver import (
    RESOLVER_CONFIG_PATH,
    Resolver,
    ResolverConfig,
)
from pooltool.physics.resolve.stick_ball import (
    StickBallModel,
    get_stick_ball_model,
)
from pooltool.physics.resolve.transition import (
    BallTransitionModel,
    get_transition_model,
)

__all__ = [
    "PhysicsEngine",
    "evolve",
    "resolve",
    "Resolver",
    "RESOLVER_CONFIG_PATH",
    "ResolverConfig",
    "BallBallModel",
    "get_ball_ball_model",
    "BallCCushionModel",
    "BallLCushionModel",
    "get_ball_circ_cushion_model",
    "get_ball_lin_cushion_model",
    "BallPocketModel",
    "get_ball_pocket_model",
    "StickBallModel",
    "get_stick_ball_model",
    "BallTransitionModel",
    "get_transition_model",
]
