"""Physics subpackage for pooltool"""

from pooltool.physics import evolve, resolve
from pooltool.physics.engine import PhysicsEngine
from pooltool.physics.resolve.ball_ball import (
    BallBallCollisionStrategy,
    BallBallModel,
    get_ball_ball_model,
)
from pooltool.physics.resolve.ball_cushion import (
    BallCCushionCollisionStrategy,
    BallCCushionModel,
    BallLCushionCollisionStrategy,
    BallLCushionModel,
    get_ball_circ_cushion_model,
    get_ball_lin_cushion_model,
)
from pooltool.physics.resolve.ball_pocket import (
    BallPocketModel,
    BallPocketStrategy,
    get_ball_pocket_model,
)
from pooltool.physics.resolve.resolver import (
    RESOLVER_CONFIG_PATH,
    Resolver,
    ResolverConfig,
)
from pooltool.physics.resolve.stick_ball import (
    StickBallCollisionStrategy,
    StickBallModel,
    get_stick_ball_model,
)
from pooltool.physics.resolve.transition import (
    BallTransitionModel,
    BallTransitionStrategy,
    get_transition_model,
)
from pooltool.physics.resolve.types import ArgType, ModelArgs
from pooltool.physics.utils import (
    get_airborne_time,
    get_ball_energy,
    get_roll_time,
    get_slide_time,
    get_spin_time,
    get_u_vec,
    rel_velocity,
    surface_velocity,
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
    "ArgType",
    "ModelArgs",
    "rel_velocity",
    "surface_velocity",
    "get_u_vec",
    "get_slide_time",
    "get_roll_time",
    "get_spin_time",
    "get_airborne_time",
    "get_ball_energy",
]
