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

        # state history
        self.history = {'t': [], 'rvw': [], 's': []}


    def store(self, t, rvw, s):
        self.history['t'].append(t)
        self.history['rvw'].append(rvw)
        self.history['s'].append(s)


    def update(self, rvw, s):
        self.rvw = rvw
        self.s = s


    def as_dataframe(self):
        t = np.array(self.history['t'])
        s = np.array(self.history['s'])
        rvw = np.array(self.history['rvw'])

        return pd.DataFrame({
            'rx': rvw[:, 0, 0], 'ry': rvw[:, 0, 1], 'rz': rvw[:, 0, 2],
            'vx': rvw[:, 1, 0], 'vy': rvw[:, 1, 1], 'vz': rvw[:, 1, 2],
            'wx': rvw[:, 2, 0], 'wy': rvw[:, 2, 1], 'wz': rvw[:, 2, 2],
            '|v|': np.sqrt(rvw[:, 1, 1]**2 + rvw[:, 1, 0]**2),
            '|w|': np.sqrt(rvw[:, 2, 2]**2 + rvw[:, 2, 1]**2 + rvw[:, 2, 0]**2),
            'time': t,
            'state': s,
        })


    def plot_history(self, full=False):
        """Primitive plotting for use during development"""
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
        add_plot(fig, 331, 'time', 'rx')
        add_plot(fig, 332, 'time', 'ry')
        add_plot(fig, 333, 'time', 'rz')
        add_plot(fig, 334, 'time', 'vx')
        add_plot(fig, 335, 'time', 'vy')
        add_plot(fig, 336, 'time', 'vz')
        add_plot(fig, 337, 'time', 'wx')
        add_plot(fig, 338, 'time', 'wy')
        add_plot(fig, 339, 'time', 'wz')
        plt.tight_layout()
        plt.show()

        if full:
            fig = plt.figure(figsize=(6, 5))
            add_plot(fig, 111, 'time', '|v|')
            plt.title(f"ball ID: {self.id}")
            plt.tight_layout()
            plt.show()

            fig = plt.figure(figsize=(6, 5))
            add_plot(fig, 111, 'time', '|w|')
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

        # rail properties
        pass

        # felt properties
        self.u_s = u_s or psim.u_s
        self.u_r = u_r or psim.u_r
        self.u_sp = u_sp or psim.u_sp


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

        v_T, w_T = physics.cue_strike(ball.m, self.M, ball.R, V0, phi, theta, a, b)

        ball.rvw[1] = v_T
        ball.rvw[2] = w_T

        if np.allclose(physics.get_rel_velocity(ball.rvw, ball.R), 0):
            ball.s = psim.rolling
        else:
            ball.s = psim.sliding


