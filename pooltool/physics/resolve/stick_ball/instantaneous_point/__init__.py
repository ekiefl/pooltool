from typing import Tuple

import attrs
import numpy as np

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball, BallState
from pooltool.objects.cue.datatypes import Cue
from pooltool.physics.resolve.stick_ball.core import CoreStickBallCollision


def cue_strike(m, M, R, V0, phi, theta, a, b, throttle_english: bool):
    """Strike a ball

                              , - ~  ,
    ◎───────────◎         , '          ' ,
    │           │       ,             ◎    ,
    │      /    │      ,              │     ,
    │     /     │     ,               │ b    ,
    ◎    / phi  ◎     ,           ────┘      ,
    │   /___    │     ,            -a        ,
    │           │      ,                    ,
    │           │       ,                  ,
    ◎───────────◎         ,               '
      bottom cushion        ' - , _ , -
                     ______________________________
                              playing surface
    Args:

    m:
        ball mass

    M:
        cue mass

    R:
        ball radius

    V0:
        What initial velocity does the cue strike the ball?

    phi:
        The direction you strike the ball in relation to the bottom cushion

    theta:
        How elevated is the cue from the playing surface, in degrees?

    a:
        How much side english should be put on? -1 being rightmost side of ball, +1
        being leftmost side of ball

    b:
        How much vertical english should be put on? -1 being bottom-most side of ball,
        +1 being topmost side of ball

    throttle_english:
        This function creates unrealistic magnitudes of spin. To compensate, this flag
        exists. If True, a 'fake' factor is added that scales down the passed a and b
        values, by an amount defined by pooltool.english_fraction
    """

    a *= R
    b *= R

    if throttle_english:
        a *= const.english_fraction
        b *= const.english_fraction

    phi *= np.pi / 180
    theta *= np.pi / 180

    I = 2 / 5 * m * R**2

    c = np.sqrt(R**2 - a**2 - b**2)

    # Calculate impact force F.  In Leckie & Greenspan, the mass term in numerator is
    # ball mass, which seems wrong.  See
    # https://billiards.colostate.edu/faq/cue-tip/force/
    numerator = 2 * M * V0
    temp = (
        a**2
        + (b * np.cos(theta)) ** 2
        + (c * np.cos(theta)) ** 2
        - 2 * b * c * np.cos(theta) * np.sin(theta)
    )
    denominator = 1 + m / M + 5 / 2 / R**2 * temp
    F = numerator / denominator

    # 3D FIXME
    # v_B = -F/m * np.array([0, np.cos(theta), np.sin(theta)])
    v_B = -F / m * np.array([0, np.cos(theta), 0])

    vec_x = -c * np.sin(theta) + b * np.cos(theta)
    vec_y = a * np.sin(theta)
    vec_z = -a * np.cos(theta)

    vec = np.array([vec_x, vec_y, vec_z])
    w_B = F / I * vec

    # Rotate to table reference
    rot_angle = phi + np.pi / 2
    v_T = ptmath.coordinate_rotation(v_B, rot_angle)
    w_T = ptmath.coordinate_rotation(w_B, rot_angle)

    return v_T, w_T


@attrs.define
class InstantaneousPoint(CoreStickBallCollision):
    throttle_english: bool

    def solve(self, cue: Cue, ball: Ball) -> Tuple[Cue, Ball]:
        v, w = cue_strike(
            ball.params.m,
            cue.specs.M,
            ball.params.R,
            cue.V0,
            cue.phi,
            cue.theta,
            cue.a,
            cue.b,
            throttle_english=self.throttle_english,
        )

        rvw = np.array([ball.state.rvw[0], v, w])
        s = const.sliding

        ball.state = BallState(rvw, s)

        return cue, ball
