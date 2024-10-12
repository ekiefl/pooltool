from time import perf_counter
import logging
_logger = logging.getLogger(__name__)
import numpy as np
import pytest

from pooltool.physics.resolve.ball_ball.frictional_mathavan import collide_balls

DEG2RAD = np.pi/180
RAD2DEG = 180/np.pi


@pytest.mark.parametrize("initial_conditions,expected", zip([
    (1.539, 58.63, 33.83),
    (1.032, 39.31, 26.36),
    (1.364, 51.96, 40.52),
    (1.731, 65.94, 46.5),
    (0.942, 35.89, 18.05)
], [
    # Table 1       # Table 2
    (0.914, 0.831,  31.93, 32.20),
    (0.520, 0.599,  32.45, 25.07),
    (0.917, 0.676,  29.91, 38.62),
    (1.28,  0.780,  27.32, 44.38),
    (0.383, 0.579,  29.47, 17.15)
]))
def test_collide_balls(initial_conditions, expected):
    """Reproduce results of Mathavan et al, 2014 - Tables 1 and 2"""
    cue_ball_velocity, topspin, cut_angle = initial_conditions
    R = 0.02625
    M = 0.1406
    e = 0.89
    mu_s = 0.21
    mu_b = 0.05
    r_i = np.zeros(3)
    rd = np.array([1.0, 0.0, 0.0])
    r_j = r_i + 2 * R * rd
    v_j = np.zeros(3, dtype=np.float64)
    omega_j = np.zeros(3, dtype=np.float64)
    c, s = np.cos(cut_angle*DEG2RAD), np.sin(cut_angle*DEG2RAD)
    v_i, omega_i = np.array(((cue_ball_velocity*c, 0.0, cue_ball_velocity*s),
                             (          topspin*s, 0.0,          -topspin*c)))
    deltaP = (1 + e) * M * cue_ball_velocity / 8000
    t0 = perf_counter()
    v_i1, omega_i1, v_j1, omega_j1 = collide_balls(r_i, v_i, omega_i,
                                                   r_j, v_j, omega_j,
                                                   R=R, M=M, u_s=mu_s, u_b=mu_b,
                                                   deltaP=deltaP)
    t1 = perf_counter()
    _logger.info('evaluation time: %s', t1-t0)
    v_iS_mag_ex, theta_i_ex, v_jS_mag_ex, theta_j_ex = expected
    # TODO
    # To calculate the expected values need to find both ball velocities upon entering pure rolling state post-collision
    # e_i, e_j = BallSlidingEvent(0.0, 0, r_i, v_i1, omega_i1), \
    #            BallSlidingEvent(0.0, 1, r_j, v_j1, omega_j1)
    # v_iS = e_i.next_motion_event.eval_velocity(0.0)
    # v_jS = e_j.next_motion_event.eval_velocity(0.0)
    # v_iS_mag = np.sqrt(np.dot(v_iS, v_iS))
    # v_jS_mag = np.sqrt(np.dot(v_jS, v_jS))
    # lambda_i = np.arctan(v_iS[2]/v_iS[0])*RAD2DEG
    # lambda_j = np.arctan(v_jS[2]/v_jS[0])*RAD2DEG
    # theta_i = abs(lambda_i - cut_angle)
    # theta_j = abs(lambda_j - cut_angle)
    # assert abs(v_iS_mag - v_iS_mag_ex)/abs(v_iS_mag_ex) < 1e-2
    # assert abs(v_jS_mag - v_jS_mag_ex)/abs(v_jS_mag_ex) < 1e-2
    # assert abs(theta_i - theta_i_ex)/abs(theta_i_ex) < 1e-2
    # assert abs(theta_j - theta_j_ex)/abs(theta_j_ex) < 1e-2
