import math

import numpy as np

import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball


class AlciatoreBallBallFriction:
    """Friction fit curve u_b = a + b * exp(-c * v_rel) used in David Alciatore's TP A-14"""

    def __init__(self, a: float = 9.951e-3, b: float = 0.108, c: float = 1.088):
        self.a = a
        self.b = b
        self.c = c

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
