import math
from typing import Protocol

import attrs

import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball
from pooltool.utils.strenum import StrEnum, auto


class BallBallFrictionModel(StrEnum):
    """An Enum for different ball-ball friction models

    Attributes:
        AVERAGE:
            The friction is calculated as the average of ball-ball sliding friction of
            the two balls.

        ALCIATORE:
            Friction fit curve :math:`u_b = a + b e^{ -c v_{rel} }` used in David Alciatore's TP A-14.
    """

    AVERAGE = auto()
    ALCIATORE = auto()


class BallBallFrictionStrategy(Protocol):
    """Ball-ball friction models must satisfy this protocol"""

    def calculate_friction(self, ball1: Ball, ball2: Ball) -> float:
        """This method calculates ball-ball friction"""
        ...


@attrs.define
class AlciatoreBallBallFriction:
    """Friction fit curve :math:`u_b = a + b * e^{ -c * v_{rel} }` used in David Alciatore's TP A-14"""

    a: float = 9.951e-3
    b: float = 0.108
    c: float = 1.088

    model: BallBallFrictionModel = attrs.field(
        default=BallBallFrictionModel.ALCIATORE, init=False, repr=False
    )

    def calculate_friction(self, ball1: Ball, ball2: Ball) -> float:
        unit_normal = ptmath.unit_vector(ball2.xyz - ball1.xyz)
        v1_c = ptmath.tangent_surface_velocity(
            ball1.state.rvw, unit_normal, ball1.params.R
        )
        v2_c = ptmath.tangent_surface_velocity(
            ball2.state.rvw, -unit_normal, ball2.params.R
        )
        relative_surface_speed = ptmath.norm3d(v1_c - v2_c)
        return self.a + self.b * math.exp(-self.c * relative_surface_speed)


@attrs.define
class AverageBallBallFriction:
    model: BallBallFrictionModel = attrs.field(
        default=BallBallFrictionModel.AVERAGE, init=False, repr=False
    )

    def calculate_friction(self, ball1: Ball, ball2: Ball) -> float:
        return (ball1.params.u_b + ball2.params.u_b) / 2


ball_ball_friction_models: dict[
    BallBallFrictionModel, type[BallBallFrictionStrategy]
] = {
    BallBallFrictionModel.AVERAGE: AverageBallBallFriction,
    BallBallFrictionModel.ALCIATORE: AlciatoreBallBallFriction,
}
