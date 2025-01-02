from typing import Dict, Optional, Protocol, Type

from pooltool.objects.ball.datatypes import Ball
from pooltool.physics.resolve.ball_ball.frictional_inelastic.friction.alciatore import (
    AlciatoreBallBallFriction,
)
from pooltool.physics.resolve.ball_ball.frictional_inelastic.friction.average import (
    AverageBallBallFriction,
)
from pooltool.utils.strenum import StrEnum, auto


class BallBallFrictionModel(StrEnum):
    """An Enum for different ball-ball friction models"""

    AVERAGE = auto()
    ALCIATORE = auto()


class BallBallFrictionStrategy(Protocol):
    """Ball-ball friction models must satisfy this protocol"""

    def calculate_friction(self, ball1: Ball, ball2: Ball) -> float:
        """This method calculates ball-ball friction"""
        ...


_ball_ball_friction_models: Dict[
    BallBallFrictionStrategy, Type[BallBallFrictionStrategy]
] = {
    BallBallFrictionModel.AVERAGE: AverageBallBallFriction,
    BallBallFrictionModel.ALCIATORE: AlciatoreBallBallFriction,
}


def get_ball_ball_friction_model(
    model: Optional[BallBallFrictionModel] = None, params: ModelArgs = {}
) -> BallBallFrictionStrategy:
    """Returns a ball-ball collision friction model for the FrictionalInelastic ball-ball collision model

    Args:
        model:
            An Enum specifying the desired model. AverageBallBallFriction is returned
            if None is passed
        params:
            A mapping of parameters accepted by the model.

    Returns:
        An instantiated model that satisfies the :class:`BallBallFrictionStrategy`
        protocol.
    """
    if model is None:
        return AverageBallBallFriction()

    return _ball_ball_friction_models[model](**params)


__all__ = [
    "BallBallFrictionModel",
    "AverageBallBallFriction",
    "AlciatoreBallBallFriction",
]
