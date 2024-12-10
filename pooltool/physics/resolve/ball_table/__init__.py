from typing import Dict, Optional, Type

from pooltool.physics.resolve.ball_table.core import BallTableCollisionStrategy
from pooltool.physics.resolve.ball_table.frictionless_inelastic import (
    FrictionlessInelastic,
)
from pooltool.physics.resolve.types import ModelArgs
from pooltool.utils.strenum import StrEnum, auto


class BallTableModel(StrEnum):
    """An Enum for different ball-table collision models

    Attributes:
        FRICTIONLESS_INELASTIC:
            The ball impacts the table with a coefficient of restitution. Spin is
            unaffected.
    """

    FRICTIONLESS_INELASTIC = auto()


_ball_table_models: Dict[BallTableModel, Type[BallTableCollisionStrategy]] = {
    BallTableModel.FRICTIONLESS_INELASTIC: FrictionlessInelastic,
}


def get_ball_table_model(
    model: Optional[BallTableModel] = None, params: ModelArgs = {}
) -> BallTableCollisionStrategy:
    """Returns a ball-table collision model

    Args:
        model:
            An Enum specifying the desired model. If not passed,
            :class:`FrictionlessInelastic` is passed with empty params.
        params:
            A mapping of parameters accepted by the model.

    Returns:
        An instantiated model that satisfies the :class:`BallTableCollisionStrategy`
        protocol.
    """
    if model is None:
        return FrictionlessInelastic()

    return _ball_table_models[model](**params)
