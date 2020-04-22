#! /usr/bin/env python

import psim
import psim.utils as utils

import numpy as np


def get_rel_velocity(rvw, R):
    _, v, w = rvw
    return v + R * np.cross(np.array([0,0,1]), w)


def resolve_ball_ball_collision(rvw1, rvw2):
    """FIXME Instantaneous, elastic, equal mass collision"""

    r1, r2 = rvw1[0], rvw2[0]
    v1, v2 = rvw1[1], rvw2[1]

    v_rel = v1 - v2
    v_mag = np.linalg.norm(v_rel)

    n = utils.unit_vector(r2 - r1)
    t = utils.coordinate_rotation(n, np.pi/2)

    alpha = utils.angle(n)
    beta = utils.angle(v_rel, n)

    rvw1[1] = t * v_mag*np.sin(beta) + v2
    rvw2[1] = n * v_mag*np.cos(beta) + v2

    return rvw1, rvw2


def get_ball_ball_collision_time(rvw1, rvw2, s1, s2, mu1, mu2, m1, m2, g, R):
    """Get the time until collision between 2 balls"""
    c1x, c1y = rvw1[0, 0], rvw1[0, 1]
    c2x, c2y = rvw2[0, 0], rvw2[0, 1]

    if s1 == psim.stationary or s1 == psim.spinning:
        a1x, a1y, b1x, b1y = 0, 0, 0, 0
    else:
        phi1 = utils.angle(rvw1[1])
        v1 = np.linalg.norm(rvw1[1])

        u1 = (np.array([1,0,0])
              if s1 == psim.rolling
              else utils.coordinate_rotation(utils.unit_vector(get_rel_velocity(rvw1, R)), -phi1))

        a1x = -1/2*mu1*g*(u1[0]*np.cos(phi1) - u1[1]*np.sin(phi1))
        a1y = -1/2*mu1*g*(u1[0]*np.sin(phi1) + u1[1]*np.cos(phi1))
        b1x = v1*np.cos(phi1)
        b1y = v1*np.sin(phi1)

    if s2 == psim.stationary or s2 == psim.spinning:
        a2x, a2y, b2x, b2y = 0, 0, 0, 0
    else:
        phi2 = utils.angle(rvw2[1])
        v2 = np.linalg.norm(rvw2[1])

        u2 = (np.array([1,0,0])
              if s2 == psim.rolling
              else utils.coordinate_rotation(utils.unit_vector(get_rel_velocity(rvw2, R)), -phi2))

        a2x = -1/2*mu2*g*(u2[0]*np.cos(phi2) - u2[1]*np.sin(phi2))
        a2y = -1/2*mu2*g*(u2[0]*np.sin(phi2) + u2[1]*np.cos(phi2))
        b2x = v2*np.cos(phi2)
        b2y = v2*np.sin(phi2)

    Ax, Ay = a2x-a1x, a2y-a1y
    Bx, By = b2x-b1x, b2y-b1y
    Cx, Cy = c2x-c1x, c2y-c1y

    a = Ax**2 + Ay**2
    b = 2*Ax*Bx + 2*Ay*By
    c = Bx**2 + 2*Ax*Cx + 2*Ay*Cy + By**2
    d = 2*Bx*Cx + 2*By*Cy
    e = Cx**2 + Cy**2 - 4*R**2

    roots = np.roots([a,b,c,d,e])

    roots = roots[
        (abs(roots.imag) <= psim.tol) & \
        (roots.real > psim.tol)
    ].real

    return roots.min() if len(roots) else np.inf


def get_ball_rail_collision_time(rvw, rail, s, mu, m, g, R):
    """Get the time until collision between ball and collision

    Parameters
    ==========
    rail : 2x2 array
        Line of the rail, ((x1,y1),(x2,y2))
    """
    if s == psim.stationary or s == psim.spinning:
        return np.inf

    r, v, w = rvw

    if rail[0,0] == 0 and rail[1,0] == 0:
        # left rail
        trig1, trig2 = np.cos, np.sin
        C = r[0] - R

    elif rail[0,0] != 0 and rail[1,0] != 0:
        # right rail
        trig1, trig2 = np.cos, np.sin
        w = rail[0, 0]
        C = r[0] - w - R

    elif rail[0,1] == 0 and rail[1,1] == 0:
        # bottom rail
        trig1, trig2 = np.sin, np.cos
        C = r[1] - R

    elif rail[0,1] != 0 and rail[1,1] != 0:
        # top rail
        trig1, trig2 = np.sin, np.cos
        l = rail[0, 1]
        C = r[1] - l - R

    else:
        raise ValueError("Only coded rails along principal axes")

    if s == psim.rolling:

        phi = utils.angle(v)
        vmag = np.linalg.norm(v)

        A = -1/2*mu*g*trig1(phi)
        B = vmag*trig1(phi)

    if s == psim.sliding:
        phi = utils.angle(v)
        v = np.linalg.norm(v)

        u = utils.coordinate_rotation(utils.unit_vector(get_rel_velocity(rvw, R)), -phi)

        #FIXME
        A = 0

        a2x = -1/2*mu2*g*(u2[0]*np.cos(phi2) - u2[1]*np.sin(phi2))
        a2y = -1/2*mu2*g*(u2[0]*np.sin(phi2) + u2[1]*np.cos(phi2))
        b2x = v2*np.cos(phi2)
        b2y = v2*np.sin(phi2)


    roots = np.roots([A,B,C])

    roots = roots[
        (abs(roots.imag) <= psim.tol) & \
        (roots.real > psim.tol)
    ].real

    return roots.min() if len(roots) else np.inf


def get_slide_time(rvw, R, u_s, g):
    return 2*np.linalg.norm(get_rel_velocity(rvw, R)) / (7*u_s*g)


def get_roll_time(rvw, u_r, g):
    _, v, _ = rvw
    return np.linalg.norm(v) / (u_r*g)


def get_spin_time(rvw, R, u_sp, g):
    _, _, w = rvw
    return np.abs(w[2]) * 2/5*R/u_sp/g


def evolve_ball_motion(state, rvw, R, m, u_s, u_sp, u_r, g, t):
    if state == psim.stationary:
        return rvw, state

    if state == psim.sliding:
        tau_slide = get_slide_time(rvw, R, u_s, g)

        if t >= tau_slide:
            rvw = evolve_slide_state(rvw, R, m, u_s, u_sp, g, tau_slide)
            state = psim.rolling
            t -= tau_slide
        else:
            return evolve_slide_state(rvw, R, m, u_s, u_sp, g, t), psim.sliding

    if state == psim.rolling:
        tau_roll = get_roll_time(rvw, u_r, g)

        if t >= tau_roll:
            rvw = evolve_roll_state(rvw, R, u_r, u_sp, g, tau_roll)
            state = psim.spinning
            t -= tau_roll
        else:
            return evolve_roll_state(rvw, R, u_r, u_sp, g, t), psim.rolling

    if state == psim.spinning:
        tau_spin = get_spin_time(rvw, R, u_sp, g)

        if t >= tau_spin:
            return evolve_perpendicular_spin_state(rvw, R, u_sp, g, tau_spin), psim.stationary
        else:
            return evolve_perpendicular_spin_state(rvw, R, u_sp, g, t), psim.spinning


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
        np.array([rvw_B[1,0]*t - 1/2*u_s*g*t**2 * u_0[0], -1/2*u_s*g*t**2 * u_0[1], 0]),
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

    # Rotate to table reference
    rot_angle = phi + np.pi/2
    v_T = utils.coordinate_rotation(v_B, rot_angle)
    w_T = utils.coordinate_rotation(w_B, rot_angle)

    return v_T, w_T

