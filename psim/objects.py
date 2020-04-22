#! /usr/bin/env python

import psim
import psim.utils as utils
import psim.physics as physics
import pandas as pd

import numpy as np


class Ball(object):
    def __init__(self, ball_id, m=None, R=None):
        self.id = ball_id

        # physical properties
        self.m = m or psim.m
        self.R = R or psim.R
        self.I = 2/5 * self.m * self.R**2

        self.rvw = np.array([[np.nan, np.nan, np.nan],  # positions (r)
                             [0,      0,      0     ],  # velocities (v)
                             [0,      0,      0     ]]) # angular velocities (w)

        # stationary=0, spinning=1, sliding=2, rolling=3
        self.s = 0


    def __repr__(self):
        lines = [
            f'<{self.__class__.__module__}.{self.__class__.__name__} object at {hex(id(self))}>',
            f' ├── id       : {self.id}',
            f' ├── state    : {self.s}',
            f' ├── position : {self.rvw[0]}',
            f' ├── velocity : {self.rvw[1]}',
            f' └── angular  : {self.rvw[2]}',
        ]

        return '\n'.join(lines) + '\n'


    def set(self, rvw, s):
        self.s = s
        self.rvw = rvw


    def as_dataframe(self):
        # FIXME exists only before history attribute was removed
        s = np.array(self.history['s'])
        rvw = np.array(self.history['rvw'])
        t = np.arange(len(s))

        return pd.DataFrame({
            'rx': rvw[:, 0, 0], 'ry': rvw[:, 0, 1], 'rz': rvw[:, 0, 2],
            'vx': rvw[:, 1, 0], 'vy': rvw[:, 1, 1], 'vz': rvw[:, 1, 2],
            'wx': rvw[:, 2, 0], 'wy': rvw[:, 2, 1], 'wz': rvw[:, 2, 2],
            '|v|': np.sqrt(rvw[:, 1, 2]**2 + rvw[:, 1, 1]**2 + rvw[:, 1, 0]**2),
            '|w|': np.sqrt(rvw[:, 2, 2]**2 + rvw[:, 2, 1]**2 + rvw[:, 2, 0]**2),
            'event_order': t,
            'state': s,
        })


    def plot_history(self, full=False):
        """Primitive plotting for use during development"""
        # FIXME exists only before history attribute was removed
        import pandas as pd
        import matplotlib.pyplot as plt

        def add_plot(fig, num, x, y):
            if np.max(np.abs(df[y])) < 0.000000001:
                df[y] = 0

            ax = fig.add_subplot(num)
            for name, group in groups:
                ax.plot(group[x], group[y], marker="o", linestyle="", label=name, ms=1.4)
            ax.set_ylabel(y)
            ax.set_xlabel(x)
            ax.legend()

        df = self.as_dataframe()

        groups = df.groupby('state')

        fig = plt.figure(figsize=(10, 10))
        plt.title(f"ball ID: {self.id}")
        add_plot(fig, 331, 'event_order', 'rx')
        add_plot(fig, 332, 'event_order', 'ry')
        add_plot(fig, 333, 'event_order', 'rz')
        add_plot(fig, 334, 'event_order', 'vx')
        add_plot(fig, 335, 'event_order', 'vy')
        add_plot(fig, 336, 'event_order', 'vz')
        add_plot(fig, 337, 'event_order', 'wx')
        add_plot(fig, 338, 'event_order', 'wy')
        add_plot(fig, 339, 'event_order', 'wz')
        plt.tight_layout()
        plt.show()

        if full:
            fig = plt.figure(figsize=(6, 5))
            add_plot(fig, 111, 'event_order', '|v|')
            plt.title(f"ball ID: {self.id}")
            plt.tight_layout()
            plt.show()

            fig = plt.figure(figsize=(6, 5))
            add_plot(fig, 111, 'event_order', '|w|')
            plt.title(f"ball ID: {self.id}")
            plt.tight_layout()
            plt.show()


class Table(object):
    def __init__(self, w=None, l=None, u_s=None, u_r=None, u_sp=None):
        self.w = w or psim.table_width
        self.l = l or psim.table_length

        self.L = 0
        self.R = self.w
        self.B = 0
        self.T = self.l

        self.center = (self.w/2, self.l/2)

        # felt properties
        self.u_s = u_s or psim.u_s
        self.u_r = u_r or psim.u_r
        self.u_sp = u_sp or psim.u_sp

        self.rails = [
            Rail(lx=1, ly=0, l0=-self.L),
            Rail(lx=1, ly=0, l0=-self.R),
            Rail(lx=0, ly=1, l0=-self.B),
            Rail(lx=0, ly=1, l0=-self.T),
        ]


class Rail(object):
    """A rail is defined by a line lx*x + ly*y + l0 = 0"""
    def __init__(self, lx, ly, l0):
        self.lx = lx
        self.ly = ly
        self.l0 = l0

        # rail properties
        pass


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
        rvw = np.array([ball.rvw[0], v, w,])

        s = (psim.rolling
             if abs(np.sum(physics.get_rel_velocity(rvw, ball.R))) <= psim.tol
             else psim.sliding)

        ball.set(rvw, s)
