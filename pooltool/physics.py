#! /usr/bin/env python
"""Compilation of physics equations implemented as functions.

A convention is upheld for the input and output variable names that is consistent across functions.
All units are SI (https://en.wikipedia.org/wiki/International_System_of_Units)

`rvw` : numpy.array
    The ball state (https://ekiefl.github.io/2020/12/20/pooltool-alg/#what-is-the-system-state).  It
    is a 3x3 numpy array where rvw[0, :] is the displacement vector (r), rvw[1, :] is the velocity
    vector (v), and rvw[2, :] is the angular velocity vector (w). For example, rvw[1, 1] refers to
    the y-component of the velocity vector.
`R` : float
    The radius of the ball.
`m` : float
    The radius of the ball.
`h` : float
    The height of the cushion.
`s` : int
    The motion state of the ball. Definitions are found in pooltool.state_dict
`mu` : float
    The coefficient of friction. If ball motion state is sliding, assume coefficient of sliding
    friction. If rolling, assume coefficient of rolling friction. If spinning, assume coefficient of
    spinning friction
`u_s` : float
    The sliding coefficient of friction.
`u_sp` : float
    The spinning coefficient of friction.
`u_r` : float
    The rolling coefficient of friction.
`g` : float
    The acceleration due to gravity felt by a ball.
"""

import pooltool
import pooltool.utils as utils

import numpy as np


def get_rel_velocity(rvw, R):
    _, v, w, _ = rvw
    return v + R * np.cross(np.array([0,0,1]), w)


def resolve_ball_ball_collision(rvw1, rvw2):
    """FIXME Instantaneous, elastic, equal mass collision"""

    r1, r2 = rvw1[0], rvw2[0]
    v1, v2 = rvw1[1], rvw2[1]

    v_rel = v1 - v2
    v_mag = np.linalg.norm(v_rel)

    n = utils.unit_vector(r2 - r1)
    t = utils.coordinate_rotation(n, np.pi/2)

    beta = utils.angle(v_rel, n)

    rvw1[1] = t * v_mag*np.sin(beta) + v2
    rvw2[1] = n * v_mag*np.cos(beta) + v2

    return rvw1, rvw2


def resolve_ball_cushion_collision(rvw, normal, R, m, h):
    """Inhwan Han (2005) 'Dynamics in Carom and Three Cushion Billiards'"""

    # orient the normal so it points away from playing surface
    normal = normal if np.dot(normal, rvw[1]) > 0 else -normal

    # Change from the table frame to the cushion frame. The cushion frame is defined by
    # the normal vector is parallel with <1,0,0>.
    psi = utils.angle(normal)
    rvw_R = utils.coordinate_rotation(rvw.T, -psi).T

    # The incidence angle--called theta_0 in paper
    phi = utils.angle(rvw_R[1]) % (2*np.pi)

    # Get mu and e
    e = get_bail_cushion_restitution(rvw_R)
    mu = get_bail_cushion_friction(rvw_R)

    # Depends on height of cushion relative to ball
    theta_a = np.arcsin(h/R - 1)

    # Eqs 14
    sx = rvw_R[1,0]*np.sin(theta_a) - rvw_R[1,2]*np.cos(theta_a) + R*rvw_R[2,1]
    sy = -rvw_R[1,1] - R*rvw_R[2,2]*np.cos(theta_a) + R*rvw_R[2,0]*np.sin(theta_a)
    c = rvw_R[1,0]*np.cos(theta_a) # 2D assumption

    # Eqs 16
    I = 2/5*m*R**2
    A = 7/2/m
    B = 1/m

    # Eqs 17 & 20
    PzE = (1 + e)*c/B
    PzS = np.sqrt(sx**2 + sy**2)/A

    if PzS <= PzE:
        # Sliding and sticking case
        PX = -sx/A*np.sin(theta_a) - (1+e)*c/B*np.cos(theta_a)
        PY = sy/A
        PZ = sx/A*np.cos(theta_a) - (1+e)*c/B*np.sin(theta_a)
    else:
        # Forward sliding case
        PX = -mu*(1+e)*c/B*np.cos(phi)*np.sin(theta_a) - (1+e)*c/B*np.cos(theta_a)
        PY = mu*(1+e)*c/B*np.sin(phi)
        PZ = mu*(1+e)*c/B*np.cos(phi)*np.cos(theta_a) - (1+e)*c/B*np.sin(theta_a)

    # Update velocity
    rvw_R[1,0] += PX/m
    rvw_R[1,1] += PY/m
    #rvw_R[1,2] += PZ/m

    # Update angular velocity
    rvw_R[2,0] += -R/I*PY*np.sin(theta_a)
    rvw_R[2,1] += R/I*(PX*np.sin(theta_a) - PZ*np.cos(theta_a))
    rvw_R[2,2] += R/I*PY*np.cos(theta_a)

    # Change back to table reference frame
    rvw = utils.coordinate_rotation(rvw_R.T, psi).T

    return rvw


def get_bail_cushion_restitution(rvw):
    """Get restitution coefficient dependent on ball state

    Parameters
    ==========
    rvw: np.array
        Assumed to be in reference frame such that <1,0,0> points
        perpendicular to the cushion, and in the direction away from the table

    Notes
    =====
    - https://essay.utwente.nl/59134/1/scriptie_J_van_Balen.pdf suggests a constant value of 0.85
    """

    return 0.85
    return max([
        0.40,
        0.50 + 0.257*rvw[1,0] - 0.044*rvw[1,0]**2
    ])


def get_bail_cushion_friction(rvw):
    """Get friction coeffecient depend on ball state

    Parameters
    ==========
    rvw: np.array
        Assumed to be in reference frame such that <1,0,0> points
        perpendicular to the cushion, and in the direction away from the table
    """

    ang = utils.angle(rvw[1])

    if ang > np.pi:
        ang = np.abs(2*np.pi - ang)

    ans = 0.2
    return ans


def get_ball_ball_collision_time(rvw1, rvw2, s1, s2, mu1, mu2, m1, m2, g1, g2, R):
    """Get the time until collision between 2 balls"""
    c1x, c1y = rvw1[0, 0], rvw1[0, 1]
    c2x, c2y = rvw2[0, 0], rvw2[0, 1]

    if s1 in pooltool.nontranslating:
        a1x, a1y, b1x, b1y = 0, 0, 0, 0
    else:
        phi1 = utils.angle(rvw1[1])
        v1 = np.linalg.norm(rvw1[1])

        u1 = (np.array([1,0,0])
              if s1 == pooltool.rolling
              else utils.coordinate_rotation(utils.unit_vector(get_rel_velocity(rvw1, R)), -phi1))

        a1x = -1/2*mu1*g1*(u1[0]*np.cos(phi1) - u1[1]*np.sin(phi1))
        a1y = -1/2*mu1*g1*(u1[0]*np.sin(phi1) + u1[1]*np.cos(phi1))
        b1x = v1*np.cos(phi1)
        b1y = v1*np.sin(phi1)

    if s2 in pooltool.nontranslating:
        a2x, a2y, b2x, b2y = 0, 0, 0, 0
    else:
        phi2 = utils.angle(rvw2[1])
        v2 = np.linalg.norm(rvw2[1])

        u2 = (np.array([1,0,0])
              if s2 == pooltool.rolling
              else utils.coordinate_rotation(utils.unit_vector(get_rel_velocity(rvw2, R)), -phi2))

        a2x = -1/2*mu2*g2*(u2[0]*np.cos(phi2) - u2[1]*np.sin(phi2))
        a2y = -1/2*mu2*g2*(u2[0]*np.sin(phi2) + u2[1]*np.cos(phi2))
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
        (abs(roots.imag) <= pooltool.tol) & \
        (roots.real > pooltool.tol)
    ].real

    return roots.min() if len(roots) else np.inf


def get_ball_linear_cushion_collision_time(rvw, s, lx, ly, l0, p1, p2, mu, m, g, R):
    """Get the time until collision between ball and linear cushion segment"""
    if s in pooltool.nontranslating:
        return np.inf

    phi = utils.angle(rvw[1])
    v = np.linalg.norm(rvw[1])

    u = (np.array([1,0,0]
         if s == pooltool.rolling
         else utils.coordinate_rotation(utils.unit_vector(get_rel_velocity(rvw, R)), -phi)))

    ax = -1/2*mu*g*(u[0]*np.cos(phi) - u[1]*np.sin(phi))
    ay = -1/2*mu*g*(u[0]*np.sin(phi) + u[1]*np.cos(phi))
    bx, by = v*np.cos(phi), v*np.sin(phi)
    cx, cy = rvw[0, 0], rvw[0, 1]

    A = lx*ax + ly*ay
    B = lx*bx + ly*by
    C1 = l0 + lx*cx + ly*cy + R*np.sqrt(lx**2 + ly**2)
    C2 = l0 + lx*cx + ly*cy - R*np.sqrt(lx**2 + ly**2)

    roots = np.append(np.roots([A,B,C1]), np.roots([A,B,C2]))

    roots = roots[
        (abs(roots.imag) <= pooltool.tol) & \
        (roots.real > pooltool.tol)
    ].real

    # All roots beyond this point are real and positive

    for i, root in enumerate(roots):
        rvw_dtau, _ = evolve_state_motion(s, np.copy(rvw), R, m, mu, 1, mu, g, root)
        s_score = - np.dot(p1 - rvw_dtau[0], p2 - p1) / np.dot(p2 - p1, p2 - p1)
        if not (0 <= s_score <= 1):
            roots[i] = np.inf

    return roots.min() if len(roots) else np.inf


def get_ball_circular_cushion_collision_time(rvw, s, a, b, r, mu, m, g, R):
    """Get the time until collision between ball and circular cushion segment

    Parameters
    ==========
    a : float
        The x-coordinate of the cushion segment's center
    b : float
        The y-coordinate of the cushion segment's center
    r : float
        The radius of the cushion segment's center
    mu : float
        The rolling or sliding coefficient of friction. Should match the value of s
    """

    if s in pooltool.nontranslating:
        return np.inf

    phi = utils.angle(rvw[1])
    v = np.linalg.norm(rvw[1])

    u = (np.array([1,0,0]
         if s == pooltool.rolling
         else utils.coordinate_rotation(utils.unit_vector(get_rel_velocity(rvw, R)), -phi)))

    ax = -1/2*mu*g*(u[0]*np.cos(phi) - u[1]*np.sin(phi))
    ay = -1/2*mu*g*(u[0]*np.sin(phi) + u[1]*np.cos(phi))
    bx, by = v*np.cos(phi), v*np.sin(phi)
    cx, cy = rvw[0, 0], rvw[0, 1]

    A = 1/2 * (ax**2 + ay**2)
    B = ax*bx + ay*by
    C = ax*(cx-a) + ay*(cy-b) + 1/2*(bx**2 + by**2)
    D = bx*(cx-a) + by*(cy-b)
    E = 1/2*(a**2 + b**2 + cx**2 + cy**2 - (r + R)**2) - (cx*a + cy*b)

    roots = np.roots([A,B,C,D,E])

    roots = roots[
        (abs(roots.imag) <= pooltool.tol) & \
        (roots.real > pooltool.tol)
    ].real

    return roots.min() if len(roots) else np.inf


def get_ball_pocket_collision_time(rvw, s, a, b, r, mu, m, g, R):
    """Get the time until collision between ball and pocket

    Parameters
    ==========
    a : float
        The x-coordinate of the pocket's center
    b : float
        The y-coordinate of the pocket's center
    r : float
        The radius of the pocket's center
    mu : float
        The rolling or sliding coefficient of friction. Should match the value of s
    """

    if s in pooltool.nontranslating:
        return np.inf

    phi = utils.angle(rvw[1])
    v = np.linalg.norm(rvw[1])

    u = (np.array([1,0,0]
         if s == pooltool.rolling
         else utils.coordinate_rotation(utils.unit_vector(get_rel_velocity(rvw, R)), -phi)))

    ax = -1/2*mu*g*(u[0]*np.cos(phi) - u[1]*np.sin(phi))
    ay = -1/2*mu*g*(u[0]*np.sin(phi) + u[1]*np.cos(phi))
    bx, by = v*np.cos(phi), v*np.sin(phi)
    cx, cy = rvw[0, 0], rvw[0, 1]

    A = 1/2 * (ax**2 + ay**2)
    B = ax*bx + ay*by
    C = ax*(cx-a) + ay*(cy-b) + 1/2*(bx**2 + by**2)
    D = bx*(cx-a) + by*(cy-b)
    E = 1/2*(a**2 + b**2 + cx**2 + cy**2 - r**2) - (cx*a + cy*b)

    roots = np.roots([A,B,C,D,E])

    roots = roots[
        (abs(roots.imag) <= pooltool.tol) & \
        (roots.real > pooltool.tol)
    ].real

    return roots.min() if len(roots) else np.inf


def get_slide_time(rvw, R, u_s, g):
    return 2*np.linalg.norm(get_rel_velocity(rvw, R)) / (7*u_s*g)


def get_roll_time(rvw, u_r, g):
    _, v, _, _ = rvw
    return np.linalg.norm(v) / (u_r*g)


def get_spin_time(rvw, R, u_sp, g):
    _, _, w, _ = rvw
    return np.abs(w[2]) * 2/5*R/u_sp/g


def get_ball_energy(rvw, R, m):
    """Rotation and kinetic energy (FIXME potential if z axis is freed)"""
    return (m*np.linalg.norm(rvw[1])**2 + (2/5*m*R**2)*np.linalg.norm(rvw[2])**2)/2


def evolve_ball_motion(state, rvw, R, m, u_s, u_sp, u_r, g, t):
    if state == pooltool.stationary or state == pooltool.pocketed:
        return rvw, state

    if state == pooltool.sliding:
        dtau_E_slide = get_slide_time(rvw, R, u_s, g)

        if t >= dtau_E_slide:
            rvw = evolve_slide_state(rvw, R, m, u_s, u_sp, g, dtau_E_slide)
            state = pooltool.rolling
            t -= dtau_E_slide
        else:
            return evolve_slide_state(rvw, R, m, u_s, u_sp, g, t), pooltool.sliding

    if state == pooltool.rolling:
        dtau_E_roll = get_roll_time(rvw, u_r, g)

        if t >= dtau_E_roll:
            rvw = evolve_roll_state(rvw, R, u_r, u_sp, g, dtau_E_roll)
            state = pooltool.spinning
            t -= dtau_E_roll
        else:
            return evolve_roll_state(rvw, R, u_r, u_sp, g, t), pooltool.rolling

    if state == pooltool.spinning:
        dtau_E_spin = get_spin_time(rvw, R, u_sp, g)

        if t >= dtau_E_spin:
            return evolve_perpendicular_spin_state(rvw, R, u_sp, g, dtau_E_spin), pooltool.stationary
        else:
            return evolve_perpendicular_spin_state(rvw, R, u_sp, g, t), pooltool.spinning


def evolve_state_motion(state, rvw, R, m, u_s, u_sp, u_r, g, t):
    """Variant of evolve_ball_motion that does not respect motion transition events"""
    if state == pooltool.stationary or state == pooltool.pocketed:
        return rvw, state
    elif state == pooltool.sliding:
        return evolve_slide_state(rvw, R, m, u_s, u_sp, g, t), pooltool.sliding
    elif state == pooltool.rolling:
        return evolve_roll_state(rvw, R, u_r, u_sp, g, t), pooltool.rolling
    elif state == pooltool.spinning:
        return evolve_perpendicular_spin_state(rvw, R, u_sp, g, t), pooltool.spinning


def evolve_slide_state(rvw, R, m, u_s, u_sp, g, t):
    if t == 0:
        return rvw

    # Angle of initial velocity in table frame
    phi = utils.angle(rvw[1])

    rvw_B0 = utils.coordinate_rotation(rvw.T, -phi).T

    # Relative velocity unit vector in ball frame
    u_0 = utils.coordinate_rotation(utils.unit_vector(get_rel_velocity(rvw, R)), -phi)

    # Calculate quantities according to the ball frame. NOTE w_B in this code block
    # is only accurate of the x and y evolution of angular velocity. z evolution of
    # angular velocity is done in the next block

    rvw_B = np.array([
        np.array([rvw_B0[1,0]*t - 1/2*u_s*g*t**2 * u_0[0], -1/2*u_s*g*t**2 * u_0[1], 0]),
        rvw_B0[1] - u_s*g*t*u_0,
        rvw_B0[2] - 5/2/R*u_s*g*t * np.cross(u_0, np.array([0,0,1])),
        rvw_B0[3] + rvw_B0[2]*t - 1/2 * 5/2/R*u_s*g*t**2 * np.cross(u_0, np.array([0,0,1])),
    ])

    # This transformation governs the z evolution of angular velocity
    rvw_B[2, 2] = rvw_B0[2, 2]
    rvw_B[3, 2] = rvw_B0[3, 2]
    rvw_B = evolve_perpendicular_spin_state(rvw_B, R, u_sp, g, t)

    # Rotate to table reference
    rvw_T = utils.coordinate_rotation(rvw_B.T, phi).T
    rvw_T[0] += rvw[0] # Add initial ball position

    return rvw_T


def evolve_roll_state(rvw, R, u_r, u_sp, g, t):
    if t == 0:
        return rvw

    r_0, v_0, w_0, e_0 = rvw

    v_0_hat = utils.unit_vector(v_0)

    r = r_0 + v_0 * t - 1/2*u_r*g*t**2 * v_0_hat
    v = v_0 - u_r*g*t * v_0_hat
    w = utils.coordinate_rotation(v/R, np.pi/2)
    e = e_0 + utils.coordinate_rotation((v_0*t - 1/2*u_r*g*t**2 * v_0_hat)/R, np.pi/2)

    # Independently evolve the z spin
    temp = evolve_perpendicular_spin_state(rvw, R, u_sp, g, t)

    w[2] = temp[2, 2]
    e[2] = temp[3, 2]

    return np.array([r, v, w, e])


def evolve_perpendicular_spin_component(wz, ez, R, u_sp, g, t):
    if t == 0:
        return wz, ez

    if abs(wz) < pooltool.tol:
        return wz, ez

    alpha = 5*u_sp*g/(2*R)

    if t > abs(wz)/alpha:
        # You can't decay past 0 angular velocity
        t = abs(wz)/alpha

    # Always decay towards 0, whether spin is +ve or -ve
    sign = 1 if wz > 0 else -1

    wz_final = wz - sign*alpha*t
    ez_final = ez + wz*t - sign*1/2*alpha*t**2

    return wz_final, ez_final


def evolve_perpendicular_spin_state(rvw, R, u_sp, g, t):
    # Otherwise ball.rvw will be modified and corresponding entry in self.history
    # FIXME framework has changed, this may not be true
    rvw = rvw.copy()

    rvw[2, 2], rvw[3, 2] = evolve_perpendicular_spin_component(rvw[2, 2], rvw[3, 2], R, u_sp, g, t)
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
      bottom cushion           ' - , _ , - 
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
        The direction you strike the ball in relation to the bottom cushion

    theta : float (degrees)
        How elevated is the cue from the playing surface, in degrees?

    a : float
        How much side english should be put on? -1 being rightmost side of ball, +1 being
        leftmost side of ball

    b : float
        How much vertical english should be put on? -1 being bottom-most side of ball, +1 being
        topmost side of ball

    Notes
    =====
    - This function creates unrealistic magnitudes of spin. To compensate, I've got a fake factor
      that scales down the passed a and b values, called pooltool.english_fraction

    """

    a *= R*pooltool.english_fraction
    b *= R*pooltool.english_fraction

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


def is_overlapping(rvw1, rvw2, R1, R2):
    return np.linalg.norm(rvw1[0] - rvw2[0]) < (R1 + R2)
