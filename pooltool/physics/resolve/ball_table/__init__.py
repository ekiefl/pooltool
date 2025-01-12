from typing import Dict, Tuple, Type, cast

import attrs

from pooltool.physics.resolve.ball_table.core import BallTableCollisionStrategy
from pooltool.physics.resolve.ball_table.frictional_inelastic import (
    FrictionalInelastic,
)
from pooltool.physics.resolve.ball_table.frictionless_inelastic import (
    FrictionlessInelastic,
)
from pooltool.physics.resolve.models import BallTableModel

_ball_table_model_registry: Tuple[Type[BallTableCollisionStrategy], ...] = (
    FrictionlessInelastic,
    FrictionalInelastic,
)

ball_table_models: Dict[BallTableModel, Type[BallTableCollisionStrategy]] = {
    cast(BallTableModel, attrs.fields_dict(cls)["model"].default): cls
    for cls in _ball_table_model_registry
}

__all__ = [
    "BallTableModel",
    "FrictionlessInelastic",
    "FrictionalInelastic",
    "ball_table_models",
]
