from typing import cast

import attrs

from pooltool.physics.resolve.ball_off_table.core import (
    BallOffTableCollisionStrategy,
)
from pooltool.physics.resolve.ball_off_table.freeze import FreezeOffTable
from pooltool.physics.resolve.models import BallOffTableModel

_ball_off_table_model_registry: tuple[type[BallOffTableCollisionStrategy], ...] = (
    FreezeOffTable,
)

ball_off_table_models: dict[
    BallOffTableModel, type[BallOffTableCollisionStrategy]
] = {
    cast(BallOffTableModel, attrs.fields_dict(cls)["model"].default): cls
    for cls in _ball_off_table_model_registry
}

__all__ = [
    "BallOffTableCollisionStrategy",
    "BallOffTableModel",
    "FreezeOffTable",
    "ball_off_table_models",
]
