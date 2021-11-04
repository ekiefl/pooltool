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

        self.balls.append(Ball('cue', **ball_kwargs))
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

        self.balls[-1].rvw[0] = [table.center[0] + 0.2, table.l/4, self.balls[-1].R]


    def get_balls_dict(self):
        return {str(ball.id): ball for ball in self.balls}


class EightBallRack(object):
    """Arrange a list of balls into 8-ball break configuration"""
    def __init__(self, spacing_factor=1e-3, ordered=False, **ball_kwargs):
        self.balls = [Ball(str(i), **ball_kwargs) for i in range(1,16)]
        self.radius = max([ball.R for ball in self.balls])
        self.spacer = spacing_factor * self.radius
        self.eff_radius = self.radius + self.spacer + pooltool.tol

        if not ordered:
            self.balls = np.random.choice(self.balls, replace=False, size=len(self.balls))

        self.balls.append(Ball('cue', **ball_kwargs))
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

        self.balls[6].rvw[0] = self.wiggle(np.array([-3*r, 3*a*r, self.radius]))
        self.balls[7].rvw[0] = self.wiggle(np.array([-1*r, 3*a*r, self.radius]))
        self.balls[8].rvw[0] = self.wiggle(np.array([+1*r, 3*a*r, self.radius]))
        self.balls[9].rvw[0] = self.wiggle(np.array([+3*r, 3*a*r, self.radius]))

        self.balls[10].rvw[0] = self.wiggle(np.array([-4*r, 4*a*r, self.radius]))
        self.balls[11].rvw[0] = self.wiggle(np.array([-2*r, 4*a*r, self.radius]))
        self.balls[12].rvw[0] = self.wiggle(np.array([+0*r, 4*a*r, self.radius]))
        self.balls[13].rvw[0] = self.wiggle(np.array([+2*r, 4*a*r, self.radius]))
        self.balls[14].rvw[0] = self.wiggle(np.array([+4*r, 4*a*r, self.radius]))


    def center(self, x, y):
        for ball in self.balls:
            ball.rvw[0,0] += x
            ball.rvw[0,1] += y


    def center_by_table(self, table):
        x = table.w/2
        y = table.l*6/8
        self.center(x, y)

        self.balls[-1].rvw[0] = [table.center[0] + 0.2, table.l/4, self.balls[-1].R]


    def get_balls_dict(self):
        return {str(ball.id): ball for ball in self.balls}


