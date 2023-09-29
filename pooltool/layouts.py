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
    def center_by_table(self, table):
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


class SnookerRack(Rack):
    """Arrange a list of balls into snooker break configuration

    Information for the snooker rack is taken from these resources:

    https://snookerfreaks.com/how-to-choose-the-right-snooker-table-buyers-guide/
    A - Baulk Line (1/5 of the length)
    B - Semi-Circle Radius (1/6 of the width)
    C - Pink Spot
    D - Black (1/11  of the length)
    https://dynamicbilliard.ca/resources/snooker-table-layout/
    https://www.lovecuesports.com/snooker-table-setup-ball-values/
    http://www.fcsnooker.co.uk/table_markings/table_markings.htm
    """

    def __init__(
        self,
        table,
        spacing_factor=1e-3,
        ordered=False,
        params: BallParams = BallParams(),
    ):
        # kerby2000:
        #  if id is just "red" looks nicer but does not work adding "i" works
        #  but not nice
        # ekiefl:
        #  Yes, but the IDs are supposed to be unique identifiers. We could
        #  solve this by adding an attribute to ball called "name", which is
        #  separate from "id"
        self.balls = [Ball(id="red" + str(i), params=params) for i in range(1, 16)]
        self.balls.append(Ball("yellow", params=params))
        self.balls.append(Ball("green", params=params))
        self.balls.append(Ball("brown", params=params))
        self.balls.append(Ball("blue", params=params))
        self.balls.append(Ball("pink", params=params))
        self.balls.append(Ball("black", params=params))
        self.balls.append(Ball("white", params=params))

        self.radius = params.R
        self.spacer = spacing_factor * self.radius
        self.eff_radius = self.radius + self.spacer

        Rack.__init__(self, table)

    def wiggle(self, xyz):
        ang = 2 * np.pi * np.random.rand()
        rad = self.spacer * np.random.rand()

        return xyz + np.array([rad * np.cos(ang), rad * np.sin(ang), 0])

    def arrange(self):
        a = np.sqrt(3)
        r = self.eff_radius

        # Arrange red balls into pyramid
        # row 1
        self.balls[0].state.rvw[0] = self.wiggle(np.array([0, 0, self.radius]))

        # row 2
        self.balls[1].state.rvw[0] = self.wiggle(np.array([-r, a * r, self.radius]))
        self.balls[2].state.rvw[0] = self.wiggle(np.array([+r, a * r, self.radius]))

        # row 3
        self.balls[3].state.rvw[0] = self.wiggle(
            np.array([-2 * r, 2 * a * r, self.radius])
        )
        self.balls[4].state.rvw[0] = self.wiggle(np.array([0, 2 * a * r, self.radius]))
        self.balls[5].state.rvw[0] = self.wiggle(
            np.array([+2 * r, 2 * a * r, self.radius])
        )

        # row 4
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

        # row 5
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
        # place pyramid of red balls
        x = table.w / 2
        y = table.l * 6 / 8 + self.radius
        self.center(x, y)

        A = table.l / 5
        B = table.w / 6
        C = table.l / 5
        D = table.l / 11

        # yellow
        self.balls[15].state.rvw[0] = [table.w / 3, table.l / 5, self.radius]
        # green
        self.balls[16].state.rvw[0] = [table.w * 2 / 3, table.l / 5, self.radius]
        # brown
        self.balls[17].state.rvw[0] = [table.w / 2, table.l / 5, self.radius]
        # blue
        self.balls[18].state.rvw[0] = [table.w / 2, table.l / 2, self.radius]
        # pink
        self.balls[19].state.rvw[0] = [table.w / 2, table.l * 3 / 4, self.radius]
        # black
        self.balls[20].state.rvw[0] = [table.w / 2, table.l * 10 / 11, self.radius]
        # white (place halfway between brown and green)
        self.balls[21].state.rvw[0] = [table.w * 7 / 12, table.l / 5, self.radius]


def get_nine_ball_rack(*args, **kwargs):
    return NineBallRack(*args, **kwargs).get_balls_dict()


def get_eight_ball_rack(*args, **kwargs):
    return EightBallRack(*args, **kwargs).get_balls_dict()


def get_three_cushion_rack(*args, **kwargs):
    return ThreeCushionRack(*args, **kwargs).get_balls_dict()


def get_snooker_rack(*args, **kwargs):
    return SnookerRack(*args, **kwargs).get_balls_dict()
