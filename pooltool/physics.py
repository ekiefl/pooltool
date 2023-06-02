#! /usr/bin/env python
"""Compilation of physics equations implemented as functions.

A convention is upheld for the input and output variable names that is consistent across
functions.  All units are SI
(https://en.wikipedia.org/wiki/International_System_of_Units)

`rvw` : numpy.array
    The ball state
    (https://ekiefl.github.io/2020/12/20/pooltool-alg/#what-is-the-system-state).  It is
    a 3x3 numpy array where rvw[0, :] is the displacement vector (r), rvw[1, :] is the
    velocity vector (v), and rvw[2, :] is the angular velocity vector (w). For example,
    rvw[1, 1] refers to the y-component of the velocity vector.
`R` : float
    The radius of the ball.
`m` : float
    The mass of the ball.
`h` : float
    The height of the cushion.
`s` : int
    The motion state of the ball. Definitions are found in pooltool.state_dict
`mu` : float
    The coefficient of friction. If ball motion state is sliding, assume coefficient of
    sliding friction. If rolling, assume coefficient of rolling friction. If spinning,
    assume coefficient of spinning friction
`u_s` : float
    The sliding coefficient of friction.
`u_sp` : float
    The spinning coefficient of friction.
`u_r` : float
    The rolling coefficient of friction.
`e_c` : float
    The cushion coefficient of restitution
`f_c` : float
    The cushion coefficient of friction
`g` : float
    The acceleration due to gravity felt by a ball.
"""

import numpy as np
from numba import jit

import pooltool.constants as const
import pooltool.math as math


def resolve_ball_ball_collision(rvw1, rvw2):
    """FIXME Instantaneous, elastic, equal mass collision"""

    r1, r2 = rvw1[0], rvw2[0]
    v1, v2 = rvw1[1], rvw2[1]

    v_rel = v1 - v2
    v_mag = np.linalg.norm(v_rel)

    n = math.unit_vector(r2 - r1)
    t = math.coordinate_rotation(n, np.pi / 2)

    beta = math.angle(v_rel, n)

    rvw1[1] = t * v_mag * np.sin(beta) + v2
    rvw2[1] = n * v_mag * np.cos(beta) + v2

    return rvw1, rvw2


def resolve_ball_cushion_collision(rvw, normal, R, m, h, e_c, f_c):
    """Inhwan Han (2005) 'Dynamics in Carom and Three Cushion Billiards'"""

    # orient the normal so it points away from playing surface
    normal = normal if np.dot(normal, rvw[1]) > 0 else -normal

    # Change from the table frame to the cushion frame. The cushion frame is defined by
    # the normal vector is parallel with <1,0,0>.
    psi = math.angle(normal)
    rvw_R = math.coordinate_rotation(rvw.T, -psi).T

    # The incidence angle--called theta_0 in paper
    phi = math.angle(rvw_R[1]) % (2 * np.pi)

    # Get mu and e
    e = get_ball_cushion_restitution(rvw_R, e_c)
    mu = get_ball_cushion_friction(rvw_R, f_c)

    # Depends on height of cushion relative to ball
    theta_a = np.arcsin(h / R - 1)

    # Eqs 14
    sx = rvw_R[1, 0] * np.sin(theta_a) - rvw_R[1, 2] * np.cos(theta_a) + R * rvw_R[2, 1]
    sy = (
        -rvw_R[1, 1]
        - R * rvw_R[2, 2] * np.cos(theta_a)
        + R * rvw_R[2, 0] * np.sin(theta_a)
    )
    c = rvw_R[1, 0] * np.cos(theta_a)  # 2D assumption

    # Eqs 16
    I = 2 / 5 * m * R**2
    A = 7 / 2 / m
    B = 1 / m

    # Eqs 17 & 20
    PzE = (1 + e) * c / B
    PzS = np.sqrt(sx**2 + sy**2) / A

    if PzS <= PzE:
        # Sliding and sticking case
        PX = -sx / A * np.sin(theta_a) - (1 + e) * c / B * np.cos(theta_a)
        PY = sy / A
        PZ = sx / A * np.cos(theta_a) - (1 + e) * c / B * np.sin(theta_a)
    else:
        # Forward sliding case
        PX = -mu * (1 + e) * c / B * np.cos(phi) * np.sin(theta_a) - (
            1 + e
        ) * c / B * np.cos(theta_a)
        PY = mu * (1 + e) * c / B * np.sin(phi)
        PZ = mu * (1 + e) * c / B * np.cos(phi) * np.cos(theta_a) - (
            1 + e
        ) * c / B * np.sin(theta_a)

    # Update velocity
    rvw_R[1, 0] += PX / m
    rvw_R[1, 1] += PY / m
    # rvw_R[1,2] += PZ/m

    # Update angular velocity
    rvw_R[2, 0] += -R / I * PY * np.sin(theta_a)
    rvw_R[2, 1] += R / I * (PX * np.sin(theta_a) - PZ * np.cos(theta_a))
    rvw_R[2, 2] += R / I * PY * np.cos(theta_a)

    # Change back to table reference frame
    rvw = math.coordinate_rotation(rvw_R.T, psi).T

    return rvw


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

    ang = math.angle(rvw[1])

    if ang > np.pi:
        ang = np.abs(2 * np.pi - ang)

    ans = f_c
    return ans


@jit(nopython=True, cache=const.numba_cache)
def rel_velocity(rvw, R):
    """Compute velocity of cloth with respect to ball's point of contact

    This vector is non-zero whenever the ball is sliding
    """
    _, v, w = rvw
    return v + R * math.cross(np.array([0.0, 0.0, 1.0], dtype=np.float64), w)


@jit(nopython=True, cache=const.numba_cache)
def get_u_vec(rvw, phi, R, s):
    if s == const.rolling:
        return np.array([1.0, 0.0, 0.0])

    rel_vel = rel_velocity(rvw, R)

    if (rel_vel == 0.0).all():
        return np.array([1.0, 0.0, 0.0])

    return math.coordinate_rotation(math.unit_vector(rel_vel), -phi)


@jit(nopython=True, cache=const.numba_cache)
def get_slide_time(rvw, R, u_s, g):
    return 2 * np.linalg.norm(rel_velocity(rvw, R)) / (7 * u_s * g)


@jit(nopython=True, cache=const.numba_cache)
def get_roll_time(rvw, u_r, g):
    _, v, _ = rvw
    return np.linalg.norm(v) / (u_r * g)


@jit(nopython=True, cache=const.numba_cache)
def get_spin_time(rvw, R, u_sp, g):
    _, _, w = rvw
    return np.abs(w[2]) * 2 / 5 * R / u_sp / g


@jit(nopython=True, cache=const.numba_cache)
def evolve_ball_motion(state, rvw, R, m, u_s, u_sp, u_r, g, t):
    if state == const.stationary or state == const.pocketed:
        return rvw, state

    if state == const.sliding:
        dtau_E_slide = get_slide_time(rvw, R, u_s, g)

        if t >= dtau_E_slide:
            rvw = evolve_slide_state(rvw, R, m, u_s, u_sp, g, dtau_E_slide)
            state = const.rolling
            t -= dtau_E_slide
        else:
            return evolve_slide_state(rvw, R, m, u_s, u_sp, g, t), const.sliding

    if state == const.rolling:
        dtau_E_roll = get_roll_time(rvw, u_r, g)

        if t >= dtau_E_roll:
            rvw = evolve_roll_state(rvw, R, u_r, u_sp, g, dtau_E_roll)
            state = const.spinning
            t -= dtau_E_roll
        else:
            return evolve_roll_state(rvw, R, u_r, u_sp, g, t), const.rolling

    if state == const.spinning:
        dtau_E_spin = get_spin_time(rvw, R, u_sp, g)

        if t >= dtau_E_spin:
            return (
                evolve_perpendicular_spin_state(rvw, R, u_sp, g, dtau_E_spin),
                const.stationary,
            )
        else:
            return evolve_perpendicular_spin_state(rvw, R, u_sp, g, t), const.spinning


@jit(nopython=True, cache=const.numba_cache)
def evolve_state_motion(state, rvw, R, m, u_s, u_sp, u_r, g, t):
    """Variant of evolve_ball_motion that does not respect motion transition events"""
    if state == const.stationary or state == const.pocketed:
        return rvw, state
    elif state == const.sliding:
        return evolve_slide_state(rvw, R, m, u_s, u_sp, g, t), const.sliding
    elif state == const.rolling:
        return evolve_roll_state(rvw, R, u_r, u_sp, g, t), const.rolling
    elif state == const.spinning:
        return evolve_perpendicular_spin_state(rvw, R, u_sp, g, t), const.spinning


@jit(nopython=True, cache=const.numba_cache)
def evolve_slide_state(rvw, R, m, u_s, u_sp, g, t):
    if t == 0:
        return rvw

    # Angle of initial velocity in table frame
    phi = math.angle(rvw[1])

    rvw_B0 = math.coordinate_rotation(rvw.T, -phi).T

    # Relative velocity unit vector in ball frame
    u_0 = math.coordinate_rotation(math.unit_vector(rel_velocity(rvw, R)), -phi)

    # Calculate quantities according to the ball frame. NOTE w_B in this code block
    # is only accurate of the x and y evolution of angular velocity. z evolution of
    # angular velocity is done in the next block

    rvw_B = np.empty((3, 3), dtype=np.float64)
    rvw_B[0, 0] = rvw_B0[1, 0] * t - 0.5 * u_s * g * t**2 * u_0[0]
    rvw_B[0, 1] = -0.5 * u_s * g * t**2 * u_0[1]
    rvw_B[0, 2] = 0
    rvw_B[1, :] = rvw_B0[1] - u_s * g * t * u_0
    rvw_B[2, :] = rvw_B0[2] - 5 / 2 / R * u_s * g * t * math.cross(
        u_0, np.array([0, 0, 1], dtype=np.float64)
    )

    # This transformation governs the z evolution of angular velocity
    rvw_B[2, 2] = rvw_B0[2, 2]
    rvw_B = evolve_perpendicular_spin_state(rvw_B, R, u_sp, g, t)

    # Rotate to table reference
    rvw_T = math.coordinate_rotation(rvw_B.T, phi).T
    rvw_T[0] += rvw[0]  # Add initial ball position

    return rvw_T


@jit(nopython=True, cache=const.numba_cache)
def evolve_roll_state(rvw, R, u_r, u_sp, g, t):
    if t == 0:
        return rvw

    r_0, v_0, w_0 = rvw

    v_0_hat = math.unit_vector(v_0)

    r = r_0 + v_0 * t - 0.5 * u_r * g * t**2 * v_0_hat
    v = v_0 - u_r * g * t * v_0_hat
    w = math.coordinate_rotation(v / R, np.pi / 2)

    # Independently evolve the z spin
    temp = evolve_perpendicular_spin_state(rvw, R, u_sp, g, t)

    w[2] = temp[2, 2]

    new_rvw = np.empty((3, 3), dtype=np.float64)
    new_rvw[0, :] = r
    new_rvw[1, :] = v
    new_rvw[2, :] = w

    return new_rvw


@jit(nopython=True, cache=const.numba_cache)
def evolve_perpendicular_spin_component(wz, R, u_sp, g, t):
    if t == 0:
        return wz

    if np.abs(wz) < const.tol:
        return wz

    alpha = 5 * u_sp * g / (2 * R)

    if t > np.abs(wz) / alpha:
        # You can't decay past 0 angular velocity
        t = np.abs(wz) / alpha

    # Always decay towards 0, whether spin is +ve or -ve
    sign = 1 if wz > 0 else -1

    wz_final = wz - sign * alpha * t
    return wz_final


@jit(nopython=True, cache=const.numba_cache)
def evolve_perpendicular_spin_state(rvw, R, u_sp, g, t):
    # Otherwise ball.state.rvw will be modified and corresponding entry in self.history
    # FIXME framework has changed, this may not be true. EDIT This is still true.
    rvw = rvw.copy()

    rvw[2, 2] = evolve_perpendicular_spin_component(rvw[2, 2], R, u_sp, g, t)
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
      bottom cushion        ' - , _ , -
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
        How much side english should be put on? -1 being rightmost side of ball, +1
        being leftmost side of ball

    b : float
        How much vertical english should be put on? -1 being bottom-most side of ball,
        +1 being topmost side of ball

    Notes
    =====
    - This function creates unrealistic magnitudes of spin. To compensate, I've got a
      fake factor that scales down the passed a and b values, called
      pooltool.english_fraction

    """

    a *= R * const.english_fraction
    b *= R * const.english_fraction

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
    v_T = math.coordinate_rotation(v_B, rot_angle)
    w_T = math.coordinate_rotation(w_B, rot_angle)

    return v_T, w_T


def get_ball_energy(rvw, R, m):
    """Get the energy of a ball

    Currently calculating linear and rotational kinetic energy. Need to add potential
    energy if z-axis is freed
    """
    # Linear
    LKE = m * np.linalg.norm(rvw[1]) ** 2 / 2

    # Rotational
    I = 2 / 5 * m * R**2
    RKE = I * np.linalg.norm(rvw[2]) ** 2 / 2

    return LKE + RKE


def is_overlapping(rvw1, rvw2, R1, R2):
    return np.linalg.norm(rvw1[0] - rvw2[0]) < (R1 + R2)
