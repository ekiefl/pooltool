#! /usr/bin/env python

import psim
import psim.utils as utils
import psim.physics as physics

from psim.ani.animate import AnimateShot

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

        self.reset_history()


    def reset_history(self):
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
        ball : engine.Ball
            A ball object
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


    def strike_cue_ball(self, **kwargs):
        self.cue.strike(ball=self.balls['cue'], **kwargs)


    def start(self, plot=True):
        for ball in self.balls.values():
            ball.reset_history()

        q = self.balls['cue']

        for t in np.arange(0, 10, 0.05):
            rvw, s = physics.evolve_ball_motion(
                rvw=q.rvw,
                R=q.R,
                m=q.m,
                u_s=self.table.u_s,
                u_sp=self.table.u_sp,
                u_r=self.table.u_r,
                g=psim.g,
                t=t,
            )
            q.store(t, *rvw, s)

        if not plot:
            return

        import pandas as pd
        import matplotlib.pyplot as plt

        fig = plt.figure(figsize=(8, 4))
        ax = fig.add_subplot(111)
        ax.set_facecolor([x/255 for x in (202,222,235)])
        ax.set_xlim(self.table.B, self.table.T)
        ax.set_ylim(self.table.L, self.table.R)
        ax.set_ylabel('x [m]')
        ax.set_xlabel('y [m]')

        rvw = np.array(q.history['rvw'])
        x = rvw[:, 0, 0]
        y = rvw[:, 0, 1]
        s = [psim.state_dict[x] for x in np.array(q.history['s'])]
        s_lookup = {v: k for k, v in psim.state_dict.items()}
        df = pd.DataFrame({'x':x, 'y':y, 'state':s})

        groups = df.groupby('state')
        for name, group in groups:
            ax.plot(
                group['y'],
                group['x'],
                marker="o",
                linestyle="",
                label=name,
                c=tuple([x/255 for x in psim.STATE_RGB[s_lookup[group['state'].iloc[0]]]]),
                ms=2.
            )
        ax.legend(loc='best', fontsize='small')
        plt.gca().invert_yaxis()
        plt.tight_layout()
        plt.show()


    def animate(self, *args, **kwargs):
        animation = AnimateShot(self, *args, **kwargs)
        animation.start()


