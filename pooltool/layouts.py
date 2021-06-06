#! /usr/bin/env python

import pooltool

from pooltool.objects.ball import Ball

import numpy as np

class NineBallRack(object):
    """Arrange a list of balls into 9-ball break configuration"""
    def __init__(self, spacing_factor=1e-3, ordered=False, **ball_kwargs):
        self.balls = [Ball(str(i), **ball_kwargs) for i in range(1,10)]
        self.radius = max([ball.R for ball in self.balls])
        self.spacer = spacing_factor * self.radius
        self.eff_radius = self.radius + self.spacer + pooltool.tol

        if not ordered:
            self.balls = np.random.choice(self.balls, replace=False, size=len(self.balls))

        self.arrange()


    def wiggle(self, xyz):
        ang = 2*np.pi*np.random.rand()
        rad = self.spacer*np.random.rand()

        return xyz + np.array([rad*np.cos(ang), rad*np.sin(ang), 0])


    def arrange(self):
        a = np.sqrt(3)
        r = self.eff_radius

        self.balls[0].rvw[0] = self.wiggle(np.array([0, 0, self.radius]))

        self.balls[1].rvw[0] = self.wiggle(np.array([-r, a*r, self.radius]))
        self.balls[2].rvw[0] = self.wiggle(np.array([+r, a*r, self.radius]))

        self.balls[3].rvw[0] = self.wiggle(np.array([-2*r, 2*a*r, self.radius]))
        self.balls[4].rvw[0] = self.wiggle(np.array([0, 2*a*r, self.radius]))
        self.balls[5].rvw[0] = self.wiggle(np.array([+2*r, 2*a*r, self.radius]))

        self.balls[6].rvw[0] = self.wiggle(np.array([-r, 3*a*r, self.radius]))
        self.balls[7].rvw[0] = self.wiggle(np.array([+r, 3*a*r, self.radius]))

        self.balls[8].rvw[0] = self.wiggle(np.array([0, 4*a*r, self.radius]))


    def center(self, x, y):
        for ball in self.balls:
            ball.rvw[0,0] += x
            ball.rvw[0,1] += y


    def center_by_table(self, table):
        x = table.w/2
        y = table.l*6/8
        self.center(x, y)
