import math
from typing import Dict, Protocol, Type

import attrs
import numpy as np

import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball
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


@attrs.define
class AlciatoreBallBallFriction:
    """Friction fit curve u_b = a + b * exp(-c * v_rel) used in David Alciatore's TP A-14"""

    a: float = 9.951e-3
    b: float = 0.108
    c: float = 1.088

    model: BallBallFrictionModel = attrs.field(
        default=BallBallFrictionModel.ALCIATORE, init=False
    )

    def calculate_friction(self, ball1: Ball, ball2: Ball) -> float:
        unit_x = np.array([1.0, 0.0, 0.0])
        v1_c = ptmath.surface_velocity(
            ball1.state.rvw, unit_x, ball1.params.R
        ) - np.array([ball1.state.rvw[1][0], 0, 0])
        v2_c = ptmath.surface_velocity(
            ball2.state.rvw, -unit_x, ball2.params.R
        ) - np.array([ball2.state.rvw[1][0], 0, 0])
        relative_surface_speed = ptmath.norm3d(v1_c - v2_c)
        return self.a + self.b * math.exp(-self.c * relative_surface_speed)


@attrs.define
class AverageBallBallFriction:
    model: BallBallFrictionModel = attrs.field(
        default=BallBallFrictionModel.AVERAGE, init=False
    )

    def calculate_friction(self, ball1: Ball, ball2: Ball) -> float:
        return (ball1.params.u_b + ball2.params.u_b) / 2


ball_ball_friction_models: Dict[
    BallBallFrictionModel, Type[BallBallFrictionStrategy]
] = {
    BallBallFrictionModel.AVERAGE: AverageBallBallFriction,
    BallBallFrictionModel.ALCIATORE: AlciatoreBallBallFriction,
}
