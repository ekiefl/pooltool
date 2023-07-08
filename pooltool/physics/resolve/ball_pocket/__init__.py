"""Defining and handling ball pocket collisions

NOTE: If this module is ever extended to support multiple treatments for ball pocket
collisions, expand this file into a file structure modelled after ../ball_ball or
../ball_cushion
"""
from typing import Dict, Optional, Protocol, Tuple, Type

import numpy as np

import pooltool.constants as const
from pooltool.objects.ball.datatypes import Ball, BallState
from pooltool.objects.table.components import Pocket
from pooltool.physics.resolve.types import ModelArgs
from pooltool.utils.strenum import StrEnum, auto


class BallPocketStrategy(Protocol):
    def resolve(
        self, ball: Ball, pocket: Pocket, inplace: bool = False
    ) -> Tuple[Ball, Pocket]:
        ...


class CanonicalBallPocket:
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


class BallPocketModel(StrEnum):
    CANONICAL = auto()


_ball_pocket_models: Dict[BallPocketModel, Type[BallPocketStrategy]] = {
    BallPocketModel.CANONICAL: CanonicalBallPocket,
}


def get_ball_pocket_model(
    model: Optional[BallPocketModel] = None, params: ModelArgs = {}
) -> BallPocketStrategy:
    if model is None:
        return CanonicalBallPocket()

    return _ball_pocket_models[model](**params)
