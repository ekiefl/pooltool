#! /usr/bin/env python

import psim
import psim.utils as utils
import psim.physics as physics

import numpy as np

from functools import partial


class Ball(object):
    def __init__(self, ball_id, m=None, R=None):
        self.id = ball_id

        # physical properties
        self.m = m or psim.m
        self.R = R or psim.R
        self.I = 2/5 * self.m * self.R**2

        self.rvw = np.array([[np.nan, np.nan, np.nan],  # positions (r)
                             [0,      0,      0     ],  # velocities (v)
                             [0,      0,      0     ],  # angular velocities (w)
                             [0,      0,      0     ]]) # angular integrations (e)

        # stationary=0, spinning=1, sliding=2, rolling=3
        self.s = 0


    def __repr__(self):
        lines = [
            f'<{self.__class__.__module__}.{self.__class__.__name__} object at {hex(id(self))}>',
            f' ├── id       : {self.id}',
            f' ├── state    : {self.s}',
            f' ├── position : {self.rvw[0]}',
            f' ├── velocity : {self.rvw[1]}',
            f' ├── angular  : {self.rvw[2]}',
            f' └── euler    : {self.rvw[3]}',
        ]

        return '\n'.join(lines) + '\n'


    def set(self, rvw, s):
        self.s = s
        self.rvw = rvw


class Table(object):
    def __init__(self, w=None, l=None, u_s=None, u_r=None, u_sp=None,
                 edge_width=None, rail_width=None, rail_height=None,
                 table_height=None):

        self.w = w or psim.table_width
        self.l = l or psim.table_length
        self.edge_width = edge_width or psim.table_edge_width
        self.rail_width = rail_width or psim.rail_width # only for visualization
        self.height = table_height or psim.table_height # only for visualization

        self.L = 0
        self.R = self.w
        self.B = 0
        self.T = self.l

        self.center = (self.w/2, self.l/2)

        # felt properties
        self.u_s = u_s or psim.u_s
        self.u_r = u_r or psim.u_r
        self.u_sp = u_sp or psim.u_sp

        self.rails = {
            'L': Rail('L', lx=1, ly=0, l0=-self.L, height=rail_height),
            'R': Rail('R', lx=1, ly=0, l0=-self.R, height=rail_height),
            'B': Rail('B', lx=0, ly=1, l0=-self.B, height=rail_height),
            'T': Rail('T', lx=0, ly=1, l0=-self.T, height=rail_height),
        }


class Rail(object):
    """A rail is defined by a line lx*x + ly*y + l0 = 0"""
    def __init__(self, rail_id, lx, ly, l0, height=None):
        self.id = rail_id

        self.lx = lx
        self.ly = ly
        self.l0 = l0

        # Defines the normal vector of the rail surface
        self.normal = np.array([self.lx, self.ly, 0])

        # rail properties
        self.height = height or psim.rail_height


class Cue(object):
    def __init__(self, M=psim.M, brand=None):
        self.M = M
        self.brand = brand


    def strike(self, ball, V0, phi, theta=None, a=None, b=None, sweet_spot=False):
        if sweet_spot:
            # b = 2/5 is the sweet spot to go directly from stationary to rolling (no sliding)
            theta, a, b = 0, 0, 2/5
        else:
            if any([theta is None, a is None, b is None]):
                raise ValueError("Cue.strike :: Must choose theta, a, and b")

        v, w = physics.cue_strike(ball.m, self.M, ball.R, V0, phi, theta, a, b)
        rvw = np.array([ball.rvw[0], v, w, ball.rvw[3]])

        s = (psim.rolling
             if abs(np.sum(physics.get_rel_velocity(rvw, ball.R))) <= psim.tol
             else psim.sliding)

        ball.set(rvw, s)
