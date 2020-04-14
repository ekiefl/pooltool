#! /usr/bin/env python

import psim
from psim.objects import Ball, Table, Cue
import psim.utils as utils
import psim.physics as physics

import numpy as np

class ShotSimulation(object):
    def __init__(self):
        self.t = 0


    def setup_test(self):
        # make a table
        self.table = Table()

        # make a cue-stick
        self.cue = Cue(brand='Predator')

        self.balls = {}

        self.balls['cue'] = Ball('cue')
        self.balls['cue'].rvw[0] = [self.table.center[0], self.table.B+0.33, 0]

        self.balls['1'] = Ball('1')
        self.balls['1'].rvw[0] = [self.table.center[0], 1.6, 0]

        self.cue.strike(
            ball = self.balls['cue'],
            V0 = 2.9,
            phi = 80,
            theta = 80,
            a = 0.2,
            b = 0.0,
        )


    def plot_history(self, ball_states=False):
        """Primitive plotting for use during development"""
        import pandas as pd
        import matplotlib.pyplot as plt

        # Table perspective
        fig = plt.figure(figsize=(5, 10))
        ax = fig.add_subplot(111)

        for ball_id, ball in self.balls.items():
            df = ball.as_dataframe()
            groups = df.groupby('state')

            for name, group in groups:
                for i, row in group.iterrows():
                    circle1 = plt.Circle((row['rx'], row['ry']), ball.R, color='r', fill=False, alpha=0.8)
                    ax.add_artist(circle1)

        plt.title('rx vs ry')
        plt.xlim(self.table.L, self.table.R)
        plt.ylim(self.table.B, self.table.T)
        plt.show()

        if ball_states:
            for ball_id, ball in self.balls.items():
                ball.plot_history()




