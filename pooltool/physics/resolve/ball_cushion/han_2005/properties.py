import numpy as np

import pooltool.ptmath as ptmath


def get_ball_cushion_restitution(rvw, e_c):
    """Get restitution coefficient dependent on ball state

    Parameters
    ==========
    rvw: np.array
        Assumed to be in reference frame such that <1,0,0> points
        perpendicular to the cushion, and in the direction away from the table

    Notes
    =====
    - https://essay.utwente.nl/59134/1/scriptie_J_van_Balen.pdf suggests a constant
      value of 0.85
    """

    return e_c
    return max([0.40, 0.50 + 0.257 * rvw[1, 0] - 0.044 * rvw[1, 0] ** 2])


def get_ball_cushion_friction(rvw, f_c):
    """Get friction coeffecient depend on ball state

    Parameters
    ==========
    rvw: np.array
        Assumed to be in reference frame such that <1,0,0> points
        perpendicular to the cushion, and in the direction away from the table
    """

    ang = ptmath.angle(rvw[1])

    if ang > np.pi:
        ang = np.abs(2 * np.pi - ang)

    ans = f_c
    return ans
