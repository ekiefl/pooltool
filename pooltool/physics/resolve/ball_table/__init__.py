from typing import cast

import attrs

from pooltool.physics.resolve.ball_table.core import BallTableCollisionStrategy
from pooltool.physics.resolve.ball_table.frictional_inelastic import (
    FrictionalInelasticTable,
)
from pooltool.physics.resolve.ball_table.frictionless_inelastic import (
    FrictionlessInelasticTable,
)
from pooltool.physics.resolve.models import BallTableModel

_ball_table_model_registry: tuple[type[BallTableCollisionStrategy], ...] = (
    FrictionlessInelasticTable,
    FrictionalInelasticTable,
)

ball_table_models: dict[BallTableModel, type[BallTableCollisionStrategy]] = {
    cast(BallTableModel, attrs.fields_dict(cls)["model"].default): cls
    for cls in _ball_table_model_registry
}

__all__ = [
    "BallTableModel",
    "FrictionlessInelasticTable",
    "FrictionalInelasticTable",
    "ball_table_models",
]
