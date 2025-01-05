from typing import Tuple

import attrs
import numpy as np

import pooltool.constants as const
import pooltool.ptmath as ptmath
from pooltool.objects.ball.datatypes import Ball, BallState
from pooltool.objects.cue.datatypes import Cue
from pooltool.physics.resolve.stick_ball.core import CoreStickBallCollision
from pooltool.physics.resolve.stick_ball.squirt import get_squirt_angle
from pooltool.ptmath.utils import coordinate_rotation


def cue_strike(m, M, R, V0, phi, theta, a, b, english_throttle: float):
    """Strike a ball

    .. code::

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
          foot rail             ' - , _ , -
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

    english_throttle:
        This modulates the amount of spin that is generated from a cue strike, where
        english_throttle < 1 produces less spin than the model's default, and
        english_throttle > 1 produces more.
    """

    a *= R
    b *= R

    a *= english_throttle
    b *= english_throttle

    phi *= np.pi / 180
    theta *= np.pi / 180

    # Moment of inertia over mass
    I_m = 2 / 5 * R**2

    c = np.sqrt(R**2 - a**2 - b**2)

    numerator = 2 * V0
    temp = (
        a**2
        + (b * np.cos(theta)) ** 2
        + (c * np.sin(theta)) ** 2
        - 2 * b * c * np.cos(theta) * np.sin(theta)
    )
    denominator = 1 + m / M + 5 / 2 / R**2 * temp
    v = numerator / denominator

    # 3D FIXME
    # v_B = -v * np.array([0, np.cos(theta), np.sin(theta)])
    v_B = -v * np.array([0, np.cos(theta), 0])

    vec_x = -c * np.sin(theta) + b * np.cos(theta)
    vec_y = a * np.sin(theta)
    vec_z = -a * np.cos(theta)

    vec = np.array([vec_x, vec_y, vec_z])
    w_B = v / I_m * vec

    # Rotate to table reference
    rot_angle = phi + np.pi / 2
    v_T = ptmath.coordinate_rotation(v_B, rot_angle)
    w_T = ptmath.coordinate_rotation(w_B, rot_angle)

    return v_T, w_T


@attrs.define
class InstantaneousPoint(CoreStickBallCollision):
    """Instantaneous and point-like stick-ball interaction

    This collision assumes the stick-ball interaction is instantaneous and point-like.

    Note:
        - A derivation of this model can be found in Dr. Dave Billiard's technical proof
          A-30 (https://billiards.colostate.edu/technical_proofs/new/TP_A-30.pdf)

    Additionally, a deflection (squirt) angle is calculated via
    :mod:`pooltool.physics.resolve.stick_ball.squirt`).
    """

    english_throttle: float = 1.0
    squirt_throttle: float = 1.0

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
            english_throttle=self.english_throttle,
        )

        alpha = get_squirt_angle(
            ball.params.m,
            cue.specs.end_mass,
            cue.a,
            self.squirt_throttle,
        )
        v = coordinate_rotation(v, alpha)

        rvw = np.array([ball.state.rvw[0], v, w])
        s = const.sliding

        ball.state = BallState(rvw, s)

        return cue, ball
