#! /usr/bin/env python

import random
from abc import ABC, abstractmethod

import numpy as np

from pooltool.objects.ball.datatypes import Ball, BallParams


class Rack(ABC):
    def __init__(self, table):
        self.arrange()
        self.center_by_table(table)

    def get_balls_dict(self):
        return {str(ball.id): ball for ball in self.balls}

    @abstractmethod
    def arrange(self):
        pass

    @abstractmethod
    def center_by_table(self):
        pass


class NineBallRack(Rack):
    """Arrange a list of balls into 9-ball break configuration"""

    def __init__(
        self,
        table,
        spacing_factor=1e-3,
        ordered=False,
        params: BallParams = BallParams(),
    ):
        self.balls = [Ball(id=str(i), params=params) for i in range(1, 10)]
        self.radius = params.R
        self.spacer = spacing_factor * self.radius
        self.eff_radius = self.radius + self.spacer

        if not ordered:
            random.shuffle(self.balls)

        self.balls.append(Ball("cue", params=params))
        Rack.__init__(self, table)

    def wiggle(self, xyz):
        ang = 2 * np.pi * np.random.rand()
        rad = self.spacer * np.random.rand()

        return xyz + np.array([rad * np.cos(ang), rad * np.sin(ang), 0])

    def arrange(self):
        a = np.sqrt(3)
        r = self.eff_radius

        self.balls[0].state.rvw[0] = self.wiggle(np.array([0, 0, self.radius]))

        self.balls[1].state.rvw[0] = self.wiggle(np.array([-r, a * r, self.radius]))
        self.balls[2].state.rvw[0] = self.wiggle(np.array([+r, a * r, self.radius]))

        self.balls[3].state.rvw[0] = self.wiggle(
            np.array([-2 * r, 2 * a * r, self.radius])
        )
        self.balls[4].state.rvw[0] = self.wiggle(np.array([0, 2 * a * r, self.radius]))
        self.balls[5].state.rvw[0] = self.wiggle(
            np.array([+2 * r, 2 * a * r, self.radius])
        )

        self.balls[6].state.rvw[0] = self.wiggle(np.array([-r, 3 * a * r, self.radius]))
        self.balls[7].state.rvw[0] = self.wiggle(np.array([+r, 3 * a * r, self.radius]))

        self.balls[8].state.rvw[0] = self.wiggle(np.array([0, 4 * a * r, self.radius]))

    def center(self, x, y):
        for ball in self.balls:
            ball.state.rvw[0, 0] += x
            ball.state.rvw[0, 1] += y

    def center_by_table(self, table):
        x = table.w / 2
        y = table.l * 6 / 8
        self.center(x, y)

        self.balls[-1].state.rvw[0] = [
            table.center[0] + 0.2,
            table.l / 4,
            self.balls[-1].params.R,
        ]


class EightBallRack(Rack):
    """Arrange a list of balls into 8-ball break configuration"""

    def __init__(
        self,
        table,
        spacing_factor=1e-3,
        ordered=False,
        params: BallParams = BallParams(),
    ):
        self.balls = [Ball(id=str(i), params=params) for i in range(1, 16)]
        self.radius = params.R
        self.spacer = spacing_factor * self.radius
        self.eff_radius = self.radius + self.spacer

        if not ordered:
            self.balls = list(
                np.random.choice(
                    np.array(self.balls), replace=False, size=len(self.balls)
                )
            )

        self.balls.append(Ball("cue", params=params))
        Rack.__init__(self, table)

    def wiggle(self, xyz):
        ang = 2 * np.pi * np.random.rand()
        rad = self.spacer * np.random.rand()

        return xyz + np.array([rad * np.cos(ang), rad * np.sin(ang), 0])

    def arrange(self):
        a = np.sqrt(3)
        r = self.eff_radius

        self.balls[0].state.rvw[0] = self.wiggle(np.array([0, 0, self.radius]))

        self.balls[1].state.rvw[0] = self.wiggle(np.array([-r, a * r, self.radius]))
        self.balls[2].state.rvw[0] = self.wiggle(np.array([+r, a * r, self.radius]))

        self.balls[3].state.rvw[0] = self.wiggle(
            np.array([-2 * r, 2 * a * r, self.radius])
        )
        self.balls[4].state.rvw[0] = self.wiggle(np.array([0, 2 * a * r, self.radius]))
        self.balls[5].state.rvw[0] = self.wiggle(
            np.array([+2 * r, 2 * a * r, self.radius])
        )

        self.balls[6].state.rvw[0] = self.wiggle(
            np.array([-3 * r, 3 * a * r, self.radius])
        )
        self.balls[7].state.rvw[0] = self.wiggle(
            np.array([-1 * r, 3 * a * r, self.radius])
        )
        self.balls[8].state.rvw[0] = self.wiggle(
            np.array([+1 * r, 3 * a * r, self.radius])
        )
        self.balls[9].state.rvw[0] = self.wiggle(
            np.array([+3 * r, 3 * a * r, self.radius])
        )

        self.balls[10].state.rvw[0] = self.wiggle(
            np.array([-4 * r, 4 * a * r, self.radius])
        )
        self.balls[11].state.rvw[0] = self.wiggle(
            np.array([-2 * r, 4 * a * r, self.radius])
        )
        self.balls[12].state.rvw[0] = self.wiggle(
            np.array([+0 * r, 4 * a * r, self.radius])
        )
        self.balls[13].state.rvw[0] = self.wiggle(
            np.array([+2 * r, 4 * a * r, self.radius])
        )
        self.balls[14].state.rvw[0] = self.wiggle(
            np.array([+4 * r, 4 * a * r, self.radius])
        )

    def center(self, x, y):
        for ball in self.balls:
            ball.state.rvw[0, 0] += x
            ball.state.rvw[0, 1] += y

    def center_by_table(self, table):
        x = table.w / 2
        y = table.l * 6 / 8
        self.center(x, y)

        self.balls[-1].state.rvw[0] = [
            table.center[0] + 0.2,
            table.l / 4,
            self.balls[-1].params.R,
        ]


class ThreeCushionRack(Rack):
    def __init__(self, table, white_to_break=True, **ball_kwargs):
        self.balls = {
            "white": Ball("white", **ball_kwargs),
            "yellow": Ball("yellow", **ball_kwargs),
            "red": Ball("red", **ball_kwargs),
        }

        self.white_to_break = white_to_break
        self.radius = max([ball.params.R for ball in self.balls.values()])

        Rack.__init__(self, table)

    def get_balls_dict(self):
        return self.balls

    def arrange(self):
        pass

    def center_by_table(self, table):
        """Based on https://www.3cushionbilliards.com/rules/106-official-us-billiard-association-rules-of-play"""
        if self.white_to_break:
            self.balls["white"].state.rvw[0] = [
                table.w / 2 + 0.1825,
                table.l / 4,
                self.radius,
            ]
            self.balls["yellow"].state.rvw[0] = [table.w / 2, table.l / 4, self.radius]
        else:
            self.balls["yellow"].state.rvw[0] = [
                table.w / 2 + 0.1825,
                table.l / 4,
                self.radius,
            ]
            self.balls["white"].state.rvw[0] = [table.w / 2, table.l / 4, self.radius]

        self.balls["red"].state.rvw[0] = [table.w / 2, table.l * 3 / 4, self.radius]


def get_nine_ball_rack(*args, **kwargs):
    return NineBallRack(*args, **kwargs).get_balls_dict()


def get_eight_ball_rack(*args, **kwargs):
    return EightBallRack(*args, **kwargs).get_balls_dict()


def get_three_cushion_rack(*args, **kwargs):
    return ThreeCushionRack(*args, **kwargs).get_balls_dict()
