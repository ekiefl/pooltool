"""Defining and handling ball pocket collisions

NOTE: If this module is ever extended to support multiple treatments for ball pocket
collisions, expand this file into a file structure modelled after ../ball_ball or
../ball_cushion
"""
from typing import Optional, Protocol, Tuple

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


BALL_POCKET_DEFAULT = CanonicalBallPocket()


def get_ball_pocket_model(
    model: Optional[BallPocketModel] = None, params: ModelArgs = {}
) -> BallPocketStrategy:
    if model is None:
        return BALL_POCKET_DEFAULT

    assert not len(params)
    assert model == BallPocketModel.CANONICAL
    return CanonicalBallPocket()
