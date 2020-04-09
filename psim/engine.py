#! /usr/bin/env python

import psim
import psim.utils as utils
import psim.physics as physics

import numpy as np

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


    def store(self, t, r, v, w, s):
        self.history['t'].append(t)
        self.history['rvw'].append(np.array([r, v, w]))
        self.history['s'].append(s)


    def update(self, r, v, w, s):
        self.rvw = np.array([r, v, w])
        self.s = s


class Cue(object):
    def __init__(self, M=psim.M, brand=None):
        self.M = M
        self.brand = brand


    def strike(self, ball, V0, phi, theta, a, b):
        v_T, w_T = physics.cue_strike(ball.m, self.M, ball.R, V0, phi, theta, a, b)

        ball.rvw[1] = v_T
        ball.rvw[2] = w_T
        ball.s = 2


class ShotSimulation(object):
    def __init__(self):
        pass


    def setup_test(self):
        # make a table
        self.table = Table()

        # make a cue-stick
        self.cue = Cue(brand='Predator')

        self.balls = {}

        # cue-ball is at table center
        self.balls['cue'] = Ball('cue')
        self.balls['cue'].rvw[0] = [self.table.center[0], self.table.B+0.33, 0]


    def start(self):
        self.cue.strike(
            ball = self.balls['cue'],
            V0 = 0.6,
            phi = 90,
            theta = 20,
            a = -0.5,
            b = 0.0,
        )

        q = self.balls['cue']

        print(f"time of slide state: {physics.get_slide_time(q.rvw[1], q.rvw[2], R=q.R, u_s=self.table.u_s, g=psim.g)}")
        print(f"time of spin state: {physics.get_spin_time(q.rvw[2], R=q.R, u_sp=self.table.u_sp, g=psim.g)}")

        for t in np.arange(0, 10, 0.05):

            r, v, w, s = physics.evolve_ball_motion(
                *q.rvw,
                R=q.R,
                m=q.m,
                u_s=self.table.u_s,
                u_sp=self.table.u_sp,
                u_r=self.table.u_r,
                g=psim.g,
                t=t,
            )

            q.store(t, r, v, w, s)

        import pandas as pd
        import matplotlib.pyplot as plt

        fig = plt.figure(figsize=(5, 10))
        ax = fig.add_subplot(111)
        ax.set_xlim(self.table.L, self.table.R)
        ax.set_ylim(self.table.B, self.table.T)

        rvw = np.array(q.history['rvw'])
        x = rvw[:, 0, 0]
        y = rvw[:, 0, 1]
        s = np.array(q.history['s'])
        df = pd.DataFrame({'x':x, 'y':y, 'state':s})

        groups = df.groupby('state')
        for name, group in groups:
            ax.plot(group['x'], group['y'], marker="o", linestyle="", label=name, ms=2.)

        ax.legend()
        plt.show()

        print(f"position after strike: {q.rvw[0]}")
        print(f"position after evolve: {r_T}")
        print()

        print(f"velocity after strike: {q.rvw[1]}")
        print(f"velocity after evolve: {v_T}")
        print()

        print(f"ang vel after strike: {q.rvw[2]}")
        print(f"ang vel after evolve: {w_T}")
        print()





