#! /usr/bin/env python

import psim
import psim.utils as utils

import numpy as np


def get_rel_velocity(rvw, R):
    _, v, w = rvw
    return v + R * np.cross(np.array([0,0,1]), w)


def get_slide_time(rvw, R, u_s, g):
    return 2*np.linalg.norm(get_rel_velocity(rvw, R)) / (7*u_s*g)


def get_roll_time(rvw, u_r, g):
    _, v, _ = rvw
    return np.linalg.norm(v) / (u_r*g)


def get_spin_time(rvw, R, u_sp, g):
    _, _, w = rvw
    return np.abs(w[2]) * 2/5*R/u_sp/g


def evolve_ball_motion(rvw, R, m, u_s, u_sp, u_r, g, t):
    # The timers for spinning and sliding start immediately
    tau_slide = get_slide_time(rvw, R, u_s, g)

    if t > tau_slide:
        rvw_sl = evolve_slide_state(rvw, R, m, u_s, u_sp, g, tau_slide)
        t -= tau_slide
    else:
        # The ball ends in sliding state
        return evolve_slide_state(rvw, R, m, u_s, u_sp, g, t), psim.sliding

    tau_roll = get_roll_time(rvw_sl, u_r, g)

    if t > tau_roll:
        rvw_ro = evolve_roll_state(rvw_sl, R, u_r, u_sp, g, tau_roll)
        t -= tau_roll
    else:
        # The ball ends in rolling state
        return evolve_roll_state(rvw_sl, R, u_r, u_sp, g, t), psim.rolling

    tau_spin = get_spin_time(rvw_ro, R, u_sp, g)

    if t >= tau_spin:
        return evolve_perpendicular_spin_state(rvw_ro, R, u_sp, g, tau_spin), psim.stationary
    else:
        return evolve_perpendicular_spin_state(rvw_ro, R, u_sp, g, t), psim.spinning


def evolve_slide_state(rvw, R, m, u_s, u_sp, g, t):
    # Angle of initial velocity in table frame
    phi = utils.angle(rvw[1])

    rvw_B = utils.coordinate_rotation(rvw.T, -phi).T

    # Relative velocity unit vector in ball frame
    u_0 = utils.coordinate_rotation(utils.unit_vector(get_rel_velocity(rvw, R)), -phi)

    # Calculate quantities according to the ball frame. NOTE w_B in this code block
    # is only accurate of the x and y evolution of angular velocity. z evolution of
    # angular velocity is done in the next block

    rvw_B = np.array([
        np.abs(u_0) * np.array([rvw_B[1,0]*t - 1/2*u_s*g*t**2, -1/2*u_s*g*t**2, 0]),
        rvw_B[1] - u_s*g*t*u_0,
        rvw_B[2] - 5/2/R*u_s*g*t * np.cross(u_0, np.array([0,0,1]))
    ])

    # This transformation governs the z evolution of angular velocity
    rvw_B = evolve_perpendicular_spin_state(rvw_B, R, u_sp, g, t)

    # Rotate to table reference
    rvw_T = utils.coordinate_rotation(rvw_B.T, phi).T
    rvw_T[0] += rvw[0]

    return rvw_T


def evolve_roll_state(rvw, R, u_r, u_sp, g, t):
    r_0, v_0, w_0 = rvw

    v_0_hat = utils.unit_vector(v_0)

    r_T = r_0 + v_0 * t - 1/2*u_r*g*t**2 * v_0_hat
    v_T = v_0 - u_r*g*t * v_0_hat
    w_T = utils.coordinate_rotation(v_T/R, np.pi/2)

    # Independently evolve the z spin
    w_T[2] = evolve_perpendicular_spin_state(rvw, R, u_sp, g, t)[2,2]

    # This transformation governs the z evolution of angular velocity
    return np.array([r_T, v_T, w_T])


def evolve_perpendicular_spin_state(rvw, R, u_sp, g, t):
    w_0 = rvw[2]

    # Always decay towards 0, whether spin is +ve or -ve
    sign = 1 if w_0[2] > 0 else -1

    # Decay to 0, but not past
    decay = min([np.abs(w_0[2]), 5/2/R*u_sp*g*t])

    rvw[2,2] -= sign * decay
    return rvw


def cue_strike(m, M, R, V0, phi, theta, a, b):
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
      bottom rail           ' - , _ , - 
                     ______________________________
                              playing surface
    Parameters
    ==========

    m : positive float
        ball mass

    M : positive float
        cue mass

    R : positive, float
        ball radius

    V0 : positive float
        What initial velocity does the cue strike the ball?

    phi : float (degrees)
        The direction you strike the ball in relation to the bottom rail

    theta : float (degrees)
        How elevated is the cue from the playing surface, in degrees?

    a : float
        How much side english should be put on? -1 being rightmost side of ball, +1 being
        leftmost side of ball

    b : float
        How much vertical english should be put on? -1 being bottom-most side of ball, +1 being
        topmost side of ball
    """

    a *= R
    b *= R

    phi *= np.pi/180
    theta *= np.pi/180

    I = 2/5 * m * R**2

    c = np.sqrt(R**2 - a**2 - b**2)

    # Calculate impact force F
    numerator = 2 * M * V0 # In Leckie & Greenspan, the mass term in numerator is ball mass,
                           # which seems wrong. See https://billiards.colostate.edu/faq/cue-tip/force/
    temp = a**2 + (b*np.cos(theta))**2 + (c*np.cos(theta))**2 - 2*b*c*np.cos(theta)*np.sin(theta)
    denominator = 1 + m/M + 5/2/R**2 * temp
    F = numerator/denominator

    # 3D FIXME
    # v_B = -F/m * np.array([0, np.cos(theta), np.sin(theta)])
    v_B = -F/m * np.array([0, np.cos(theta), 0])
    w_B = F/I * np.array([-c*np.sin(theta) + b*np.cos(theta), a*np.sin(theta), -a*np.cos(theta)])

    print(w_B)

    # Rotate to table reference
    rot_angle = phi + np.pi/2
    v_T = utils.coordinate_rotation(v_B, rot_angle)
    w_T = utils.coordinate_rotation(w_B, rot_angle)

    print(w_T)

    return v_T, w_T

