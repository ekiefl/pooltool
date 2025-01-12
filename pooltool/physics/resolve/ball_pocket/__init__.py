"""Defining and handling ball pocket collisions

Note:
    If this module is ever extended to support multiple treatments for ball pocket
    collisions, expand this file into a file structure modelled after ../ball_ball or
    ../ball_cushion
"""

from typing import Dict, Protocol, Tuple, Type, cast

import attrs
import numpy as np

import pooltool.constants as const
from pooltool.objects.ball.datatypes import Ball, BallState
from pooltool.objects.table.components import Pocket
from pooltool.physics.resolve.models import BallPocketModel


class BallPocketStrategy(Protocol):
    """Ball-pocket collision models must satisfy this protocol"""

    def resolve(
        self, ball: Ball, pocket: Pocket, inplace: bool = False
    ) -> Tuple[Ball, Pocket]:
        """This method resolves a ball-circular cushion collision"""
        ...


@attrs.define
class CanonicalBallPocket:
    model: BallPocketModel = attrs.field(
        default=BallPocketModel.CANONICAL, init=False, repr=False
    )

    def resolve(
        self, ball: Ball, pocket: Pocket, inplace: bool = False
    ) -> Tuple[Ball, Pocket]:
        if not inplace:
            ball = ball.copy()
            pocket = pocket.copy()

        # Ball is placed at the pocket center
        rvw = np.array(
            [
                [pocket.a, pocket.b, -pocket.depth],
                [0, 0, 0],
                [0, 0, 0],
            ]
        )

        ball.state = BallState(rvw, const.pocketed)
        pocket.add(ball.id)

        return ball, pocket


_ball_pocket_model_registry: Tuple[Type[BallPocketStrategy], ...] = (
    CanonicalBallPocket,
)

ball_pocket_models: Dict[BallPocketModel, Type[BallPocketStrategy]] = {
    cast(BallPocketModel, attrs.fields_dict(cls)["model"].default): cls
    for cls in _ball_pocket_model_registry
}
