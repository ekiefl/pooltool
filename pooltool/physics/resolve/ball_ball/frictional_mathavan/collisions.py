"""
This module implements the ball-ball collision model described in: ::

  NUMERICAL SIMULATIONS OF THE FRICTIONAL COLLISIONS
  OF SOLID BALLS ON A ROUGH SURFACE
  S. Mathavan,  M. R. Jackson,  R. M. Parkin
  DOI: 10.1007/s12283-014-0158-y
  International Sports Engineering Association
  2014

"""
from logging import getLogger
_logger = getLogger(__name__)
import sys
from math import sqrt
import ctypes
from ctypes import c_double, POINTER, cast
c_double_p = POINTER(c_double)

import os.path as path
import numpy as np
from numpy import dot, array
from numpy.ctypeslib import ndpointer


INCH2METER = 0.0254
INF = float('inf')
_k = array([0, 1, 0], dtype=np.float64)


try:
    _lib = ctypes.cdll.LoadLibrary(path.join(path.dirname(path.abspath(__file__)),
                                             '_collisions.so'))
except:
    _lib = ctypes.cdll.LoadLibrary(path.join(path.dirname(path.abspath(__file__)),
                                             'collisions.dll'))
_lib.collide_balls.argtypes = (ctypes.c_double,
                               c_double_p,
                               c_double_p,
                               c_double_p,
                               c_double_p,
                               c_double_p,
                               c_double_p,
                               c_double_p,
                               c_double_p,
                               c_double_p,
                               c_double_p)

_lib.print_params.argtypes = []

_module_vars = ('M', 'R', 'mu_s', 'mu_b', 'e')
_M, _R, _mu_s, _mu_b, _e = [ctypes.c_double.in_dll(_lib, p)
                            for p in _module_vars]
M = _M.value
R = _R.value
mu_s = _mu_s.value
mu_b = _mu_b.value
e = _e.value


def set_params(**params):
    for k, v in ((k, v) for k, v in params.items()
                 if k in _module_vars):
        setattr(sys.modules[__name__], k, v)
        getattr(sys.modules[__name__], '_'+k).value = v
    # print_params()


def print_params():
    _lib.print_params()


def collide_balls_f90(r_i, v_i, omega_i,
                      r_j, v_j, omega_j,
                      deltaP, return_all=False):
    _lib.collide_balls(deltaP,
                       cast(r_i.ctypes.data, c_double_p),
                       cast(v_i.ctypes.data, c_double_p),
                       cast(omega_i.ctypes.data, c_double_p),
                       cast(r_j.ctypes.data, c_double_p),
                       cast(v_j.ctypes.data, c_double_p),
                       cast(omega_j.ctypes.data, c_double_p),
                       *collide_balls_f90.outp)
    return collide_balls_f90.out
collide_balls_f90.out = (np.zeros(3, dtype=np.float64),
                         np.zeros(3, dtype=np.float64),
                         np.zeros(3, dtype=np.float64),
                         np.zeros(3, dtype=np.float64))
collide_balls_f90.outp = tuple(cast(v.ctypes.data, c_double_p) for v in collide_balls_f90.out)


def collide_balls(r_i, v_i, omega_i,
                  r_j, v_j, omega_j,
                  deltaP=None,
                  return_all=False):
    r_ij = r_j - r_i
    r_ij_mag_sqrd = dot(r_ij, r_ij)
    # D = 2*R
    # assert  abs(r_ij_mag_sqrd - D**2) / D**2  <  1e-8, "abs(r_ij_mag_sqrd - D**2) / D**2 = %s" % (abs(r_ij_mag_sqrd - D**2) / D**2)
    r_ij_mag = sqrt(r_ij_mag_sqrd)
    z_loc = _k
    y_loc = r_ij / r_ij_mag
    x_loc = array((-y_loc[2], 0, y_loc[0]))
    G = np.vstack((x_loc, y_loc, z_loc))
    v_ix, v_iy = dot(v_i, x_loc), dot(v_i, y_loc)
    v_jx, v_jy = dot(v_j, x_loc), dot(v_j, y_loc)
    omega_ix, omega_iy, omega_iz = dot(G, omega_i)
    omega_jx, omega_jy, omega_jz = dot(G, omega_j)
    u_iR_x, u_iR_y = v_ix + R*omega_iy, v_iy - R*omega_ix
    u_jR_x, u_jR_y = v_jx + R*omega_jy, v_jy - R*omega_jx
    u_iR_xy_mag = sqrt(u_iR_x**2 + u_iR_y**2)
    u_jR_xy_mag = sqrt(u_jR_x**2 + u_jR_y**2)
    u_ijC_x = v_ix - v_jx - R*(omega_iz + omega_jz)
    u_ijC_z = R*(omega_ix + omega_jx)
    u_ijC_xz_mag = sqrt(u_ijC_x**2 + u_ijC_z**2)
    v_ijy = v_jy - v_iy
    if deltaP is None:
        deltaP = 0.5 * (1 + e) * M * abs(v_ijy) / 1000
    deltaP__2 = 0.5 * deltaP
    W_f = INF
    W_c = None
    W = 0
    niters = 0
    if return_all:
        v_is = [array((v_ix, v_iy, 0))]
        v_js = [array((v_jx, v_jy, 0))]
        omega_is = [array((omega_ix, omega_iy, omega_iz))]
        omega_js = [array((omega_jx, omega_jy, omega_jz))]
    while v_ijy < 0 or W < W_f:
        # determine impulse deltas:
        if u_ijC_xz_mag < 1e-16:
            deltaP_1 = deltaP_2 = 0
            deltaP_ix = deltaP_iy = deltaP_jx = deltaP_jy = 0
        else:
            deltaP_1 = -mu_b * deltaP * u_ijC_x / u_ijC_xz_mag
            if abs(u_ijC_z) < 1e-16:
                deltaP_2 = 0
                deltaP_ix = deltaP_iy = deltaP_jx = deltaP_jy = 0
            else:
                deltaP_2 = -mu_b * deltaP * u_ijC_z / u_ijC_xz_mag
                if deltaP_2 > 0:
                    deltaP_ix = deltaP_iy = 0
                    if u_jR_xy_mag == 0:
                        deltaP_jx = deltaP_jy = 0
                    else:
                        deltaP_jx = -mu_s * (u_jR_x / u_jR_xy_mag) * deltaP_2
                        deltaP_jy = -mu_s * (u_jR_y / u_jR_xy_mag) * deltaP_2
                else:
                    deltaP_jx = deltaP_jy = 0
                    if u_iR_xy_mag == 0:
                        deltaP_ix = deltaP_iy = 0
                    else:
                        deltaP_ix = mu_s * (u_iR_x / u_iR_xy_mag) * deltaP_2
                        deltaP_iy = mu_s * (u_iR_y / u_iR_xy_mag) * deltaP_2
        # calc velocity changes:
        deltaV_ix = ( deltaP_1 + deltaP_ix) / M
        deltaV_iy = (-deltaP   + deltaP_iy) / M
        deltaV_jx = (-deltaP_1 + deltaP_jx) / M
        deltaV_jy = ( deltaP   + deltaP_jy) / M
        # calc angular velocity changes:
        _ = 5/(2*M*R)
        deltaOm_ix = _ * ( deltaP_2 + deltaP_iy)
        deltaOm_iy = _ * (-deltaP_ix)
        deltaOm_iz = _ * (-deltaP_1)
        deltaOm_j = _ * array([( deltaP_2 + deltaP_jy),
                               (-deltaP_jx),
                               (-deltaP_1)])
        # update velocities:
        v_ix += deltaV_ix
        v_jx += deltaV_jx
        v_iy += deltaV_iy
        v_jy += deltaV_jy
        # update angular velocities:
        omega_ix += deltaOm_ix
        omega_iy += deltaOm_iy
        omega_iz += deltaOm_iz
        omega_jx += deltaOm_j[0]
        omega_jy += deltaOm_j[1]
        omega_jz += deltaOm_j[2]
        # update ball-table slips:
        u_iR_x, u_iR_y = v_ix + R*omega_iy, v_iy - R*omega_ix
        u_jR_x, u_jR_y = v_jx + R*omega_jy, v_jy - R*omega_jx
        u_iR_xy_mag = sqrt(u_iR_x**2 + u_iR_y**2)
        u_jR_xy_mag = sqrt(u_jR_x**2 + u_jR_y**2)
        # update ball-ball slip:
        u_ijC_x = v_ix - v_jx - R*(omega_iz + omega_jz)
        u_ijC_z = R*(omega_ix + omega_jx)
        u_ijC_xz_mag = sqrt(u_ijC_x**2 + u_ijC_z**2)
        # increment work:
        v_ijy0 = v_ijy
        v_ijy = v_jy - v_iy
        deltaW = deltaP__2 * abs(v_ijy0 + v_ijy)
        W += deltaW
        niters += 1
        if return_all:
            v_is.append(array((v_ix, v_iy, 0)))
            v_js.append(array((v_jx, v_jy, 0)))
            omega_is.append(array((omega_ix, omega_iy, omega_iz)))
            omega_js.append(array((omega_jx, omega_jy, omega_jz)))
        if W_c is None and v_ijy > 0:
            W_c = W
            W_f = (1 + e**2) * W_c
            # niters_c = niters
            # _logger.debug('''
            # END OF COMPRESSION PHASE
            # W_c = %s
            # W_f = %s
            # niters_c = %s
            # ''', W_c, W_f, niters_c)
    # _logger.debug('''
    # END OF RESTITUTION PHASE
    # niters_r = %s
    # ''', niters - niters_c)
    if return_all:
        v_is = array(v_is)
        v_js = array(v_js)
        omega_is = array(omega_is)
        omega_js = array(omega_js)
        for i in range(len(v_is)):
            dot(G.T, v_is[i], out=v_is[i])
            dot(G.T, v_js[i], out=v_js[i])
            dot(G.T, omega_is[i], out=omega_is[i])
            dot(G.T, omega_js[i], out=omega_js[i])
        return v_is, omega_is, v_js, omega_js
    v_i = array((v_ix, v_iy, 0))
    v_j = array((v_jx, v_jy, 0))
    omega_i = array((omega_ix, omega_iy, omega_iz))
    omega_j = array((omega_jx, omega_jy, omega_jz))
    G_T = G.T
    return dot(G_T, v_i), dot(G_T, omega_i), dot(G_T, v_j), dot(G_T, omega_j)
