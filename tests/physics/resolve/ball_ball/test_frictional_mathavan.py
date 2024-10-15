import numpy as np
import pytest

import pooltool as pt
from pooltool.physics.resolve.ball_ball.frictional_mathavan import _collide_balls

DEG2RAD = np.pi / 180
RAD2DEG = 180 / np.pi


@pytest.mark.parametrize(
    "initial_conditions,expected",
    zip(
        [
            (1.539, 58.63, 33.83),
            (1.032, 39.31, 26.36),
            (1.364, 51.96, 40.52),
            (1.731, 65.94, 46.5),
            (0.942, 35.89, 18.05),
        ],
        [
            # Table 1       # Table 2
            (0.914, 0.831, 31.93, 32.20),
            (0.520, 0.599, 32.45, 25.07),
            (0.917, 0.676, 29.91, 38.62),
            (1.28, 0.780, 27.32, 44.38),
            (0.383, 0.579, 29.47, 17.15),
        ],
    ),
)
def test_collide_balls(initial_conditions, expected):
    """Reproduce results of Mathavan et al, 2014 - Tables 1 and 2"""
    cue_ball_velocity, topspin, cut_angle = initial_conditions
    R = 0.02625
    M = 0.1406
    e_b = 0.89
    mu_s = 0.21
    mu_b = 0.05
    g = 9.81
    # cue ball state:
    r_i = np.zeros(3)
    c, s = np.cos(cut_angle * DEG2RAD), np.sin(cut_angle * DEG2RAD)
    v_i = np.array([cue_ball_velocity * c, cue_ball_velocity * s, 0.0])
    w_i = np.array([-topspin * s, topspin * c, 0.0])
    # object ball state:
    r_j = r_i + 2 * R * np.array([1.0, 0.0, 0.0])
    v_j = np.zeros(3, dtype=np.float64)
    w_j = np.zeros(3, dtype=np.float64)
    # calc immediate post-collision state
    v_i1, w_i1, v_j1, w_j1 = _collide_balls(
        r_i, v_i, w_i, r_j, v_j, w_j, R=R, M=M, u_s1=mu_s, u_s2=mu_s, u_b=mu_b, e_b=e_b
    )

    v_iS_mag_ex, v_jS_mag_ex, theta_i_ex, theta_j_ex = expected

    def calc_rolling_velocity(v, w):
        rvw = np.zeros((3, 3), dtype=np.float64)
        rvw[1], rvw[2] = v, w
        u = pt.ptmath.rel_velocity(rvw, R)
        a = -mu_s * g * u / np.linalg.norm(u)
        return v + a * pt.ptmath.get_slide_time(rvw, R, mu_s, g)

    v_iS = calc_rolling_velocity(v_i1, w_i1)
    v_jS = calc_rolling_velocity(v_j1, w_j1)
    v_iS_mag = pt.ptmath.norm2d(v_iS)
    v_jS_mag = pt.ptmath.norm2d(v_jS)
    assert abs(v_iS_mag - v_iS_mag_ex) / abs(v_iS_mag_ex) < 1e-2
    assert abs(v_jS_mag - v_jS_mag_ex) / abs(v_jS_mag_ex) < 1e-2

    lambda_i = np.arctan(v_iS[1] / v_iS[0]) * RAD2DEG
    lambda_j = np.arctan(v_jS[1] / v_jS[0]) * RAD2DEG
    theta_i = abs(lambda_i - cut_angle)
    theta_j = abs(lambda_j - cut_angle)
    assert abs(theta_i - theta_i_ex) / abs(theta_i_ex) < 1e-2
    assert abs(theta_j - theta_j_ex) / abs(theta_j_ex) < 1e-2
