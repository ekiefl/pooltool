#! /usr/bin/env python

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from collections import Counter
from typing import Dict, List, Optional, Set, Tuple, Union

import attrs
import numpy as np
from numpy.typing import NDArray

from pooltool.game.datatypes import GameType
from pooltool.objects.ball.datatypes import Ball, BallParams
from pooltool.objects.table.datatypes import Table
from pooltool.utils.strenum import StrEnum, auto


class Dir(StrEnum):
    """Movement directions

    The diagonal positions are not true diagonals (45 degrees), but rather the
    diagonals seen when creating a triangular rack pattern (60 degrees).
    """

    LEFT = auto()
    RIGHT = auto()
    UP = auto()
    DOWN = auto()
    UPRIGHT = auto()
    DOWNRIGHT = auto()
    DOWNLEFT = auto()
    UPLEFT = auto()

    @staticmethod
    def get_translation(
        direction: Dir, quantity: int, radius: float
    ) -> Tuple[float, float]:
        a = np.sqrt(3)
        translations = {
            Dir.LEFT: (-2 * radius, 0),
            Dir.RIGHT: (2 * radius, 0),
            Dir.UP: (0, 2 * radius),
            Dir.DOWN: (0, -2 * radius),
            Dir.UPRIGHT: (radius, a * radius),
            Dir.DOWNRIGHT: (radius, -a * radius),
            Dir.UPLEFT: (-radius, a * radius),
            Dir.DOWNLEFT: (-radius, -a * radius),
        }

        delta_x, delta_y = translations[direction]
        return delta_x * quantity, delta_y * quantity


@attrs.define
class Trans:
    """A translation in a direction

    Attributes:
        direction:
            A direction.
        quantity:
            The number of ball diameters to move in the direction. quantity=1
            means moving one ball diameter in the given direction.
    """

    direction: Dir
    quantity: int


@attrs.define
class Pos:
    """Defines a position relative to another position, or an anchor

    Attributes:
        loc:
            A sequence of translations.
        relative_to:
            This defines what the translation is with respect to. This can
            either be another Pos, or a 2D coordinate, normalized by the table's
            width and height. The origin is the bottom-left corner of the table,
            so (0.0, 0.0) is bottom-left and (1.0, 1.0) is top right.
    """

    loc: List[Trans]
    relative_to: Union[Pos, Tuple[float, float]]


@attrs.define
class BallPos(Pos):
    """A subclass of Pos with ball id info

    Attributes:
        ids:
            This set says which ball ids can exist at the given position.
    """

    ids: Set[str]


def _get_ball_ids(positions: List[BallPos]) -> Set[str]:
    ids = set()
    for pos in positions:
        ids.update(pos.ids)
    return ids


def _get_anchor_translation(ball: BallPos) -> Tuple[Tuple[float, float], List[Trans]]:
    """Traverse the ball position's parent hierarchy until the anchor is found"""

    translation_from_anchor: List[Trans] = []
    translation_from_anchor.extend(ball.loc)

    parent = ball.relative_to

    while True:
        if isinstance(parent, tuple):
            return parent, translation_from_anchor

        translation_from_anchor.extend(parent.loc)
        parent = parent.relative_to


def get_rack(blueprint: List[BallPos], table: Table) -> Dict[str, Ball]:
    """Generate Ball objects based on a given blueprint and table dimensions.

    The function calculates the absolute position of each ball on the table using the
    translations provided in the blueprint relative to table anchors. It then randomly
    assigns ball IDs to each position, ensuring no ball ID is used more than once.

    Args:
        blueprint:
            A list of ball positions represented as BallPos objects, which
            describe their location relative to table anchors or other
            positions.
        table:
            A Table. This must exist so the rack can be created with respect to
            the table's dimensions.
        ball_params:
            A BallParams object, which all balls will be created with. This
            contains info like ball radius.

    Returns:
        balls:
            A dictionary mapping ball IDs to their respective Ball objects, with
            their absolute positions on the table.

    Notes:
    - The table dimensions are normalized such that the bottom-left corner is
      (0.0, 0.0) and the top-right corner is (1.0, 1.0).
    """

    ball_ids = _get_ball_ids(blueprint)
    params = BallParams.default()
    radius = params.R

    balls: Dict[str, Ball] = {}

    for ball in blueprint:
        (x, y), translation = _get_anchor_translation(ball)

        x *= table.w
        y *= table.l

        for trans in translation:
            dx, dy = Dir.get_translation(trans.direction, trans.quantity, radius)
            x += dx
            y += dy

        # Choose ball
        remaining = ball_ids.intersection(ball.ids)
        assert len(remaining), "Ball requirements of blueprint unsatisfiable"
        ball_id = random.choice(list(remaining))
        ball_ids.remove(ball_id)

        # Create ball
        balls[ball_id] = Ball.create(ball_id, xy=(x, y))

    return balls


# row1_anchor = Pos(loc=[], relative_to=None)
# row2_anchor = Pos([Trans(Dir.DOWNLEFT, 1)], relative_to=row1_anchor)
# row3_anchor = Pos([Trans(Dir.DOWNLEFT, 1)], relative_to=row2_anchor)
# row4_anchor = Pos([Trans(Dir.DOWNRIGHT, 1)], relative_to=row3_anchor)
# row5_anchor = Pos([Trans(Dir.DOWNRIGHT, 1)], relative_to=row4_anchor)
#
# others = ["2", "3", "4", "5", "6", "7", "8"]
#
# blueprint = [
#    # Row 1
#    BallPos([], row1_anchor, ["1"]),
#    # Row 2
#    BallPos([], row2_anchor, others),
#    BallPos([Trans(Dir.RIGHT, 1)], row2_anchor, others),
#    # Row 3
#    BallPos([], row3_anchor, others),
#    BallPos([Trans(Dir.RIGHT, 1)], row3_anchor, ["9"]),
#    BallPos([Trans(Dir.RIGHT, 2)], row3_anchor, others),
#    # Row 4
#    BallPos([], row4_anchor, others),
#    BallPos([Trans(Dir.RIGHT, 1)], row4_anchor, others),
#    # Row 5
#    BallPos([], row5_anchor, others),
# ]

# ------------------------------------------------


def wiggle(xyz: NDArray, spacer: float):
    ang = 2 * np.pi * np.random.rand()
    rad = spacer * np.random.rand()

    return xyz + np.array([rad * np.cos(ang), rad * np.sin(ang), 0])


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

    def arrange(self):
        a = np.sqrt(3)
        r = self.eff_radius

        self.balls[0].state.rvw[0] = wiggle(np.array([0, 0, self.radius]), self.spacer)

        self.balls[1].state.rvw[0] = wiggle(
            np.array([-r, a * r, self.radius]), self.spacer
        )
        self.balls[2].state.rvw[0] = wiggle(
            np.array([+r, a * r, self.radius]), self.spacer
        )

        self.balls[3].state.rvw[0] = wiggle(
            np.array([-2 * r, 2 * a * r, self.radius]), self.spacer
        )
        self.balls[4].state.rvw[0] = wiggle(
            np.array([0, 2 * a * r, self.radius]), self.spacer
        )
        self.balls[5].state.rvw[0] = wiggle(
            np.array([+2 * r, 2 * a * r, self.radius]), self.spacer
        )

        self.balls[6].state.rvw[0] = wiggle(
            np.array([-r, 3 * a * r, self.radius]), self.spacer
        )
        self.balls[7].state.rvw[0] = wiggle(
            np.array([+r, 3 * a * r, self.radius]), self.spacer
        )

        self.balls[8].state.rvw[0] = wiggle(
            np.array([0, 4 * a * r, self.radius]), self.spacer
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

    def arrange(self):
        a = np.sqrt(3)
        r = self.eff_radius

        self.balls[0].state.rvw[0] = wiggle(np.array([0, 0, self.radius]), self.spacer)

        self.balls[1].state.rvw[0] = wiggle(
            np.array([-r, a * r, self.radius]), self.spacer
        )
        self.balls[2].state.rvw[0] = wiggle(
            np.array([+r, a * r, self.radius]), self.spacer
        )

        self.balls[3].state.rvw[0] = wiggle(
            np.array([-2 * r, 2 * a * r, self.radius]), self.spacer
        )
        self.balls[4].state.rvw[0] = wiggle(
            np.array([0, 2 * a * r, self.radius]), self.spacer
        )
        self.balls[5].state.rvw[0] = wiggle(
            np.array([+2 * r, 2 * a * r, self.radius]), self.spacer
        )

        self.balls[6].state.rvw[0] = wiggle(
            np.array([-3 * r, 3 * a * r, self.radius]), self.spacer
        )
        self.balls[7].state.rvw[0] = wiggle(
            np.array([-1 * r, 3 * a * r, self.radius]), self.spacer
        )
        self.balls[8].state.rvw[0] = wiggle(
            np.array([+1 * r, 3 * a * r, self.radius]), self.spacer
        )
        self.balls[9].state.rvw[0] = wiggle(
            np.array([+3 * r, 3 * a * r, self.radius]), self.spacer
        )

        self.balls[10].state.rvw[0] = wiggle(
            np.array([-4 * r, 4 * a * r, self.radius]), self.spacer
        )
        self.balls[11].state.rvw[0] = wiggle(
            np.array([-2 * r, 4 * a * r, self.radius]), self.spacer
        )
        self.balls[12].state.rvw[0] = wiggle(
            np.array([+0 * r, 4 * a * r, self.radius]), self.spacer
        )
        self.balls[13].state.rvw[0] = wiggle(
            np.array([+2 * r, 4 * a * r, self.radius]), self.spacer
        )
        self.balls[14].state.rvw[0] = wiggle(
            np.array([+4 * r, 4 * a * r, self.radius]), self.spacer
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

    def arrange(self):
        a = np.sqrt(3)
        r = self.eff_radius

        # Arrange red balls into pyramid
        # row 1
        self.balls[0].state.rvw[0] = wiggle(np.array([0, 0, self.radius]), self.spacer)

        # row 2
        self.balls[1].state.rvw[0] = wiggle(
            np.array([-r, a * r, self.radius]), self.spacer
        )
        self.balls[2].state.rvw[0] = wiggle(
            np.array([+r, a * r, self.radius]), self.spacer
        )

        # row 3
        self.balls[3].state.rvw[0] = wiggle(
            np.array([-2 * r, 2 * a * r, self.radius]), self.spacer
        )
        self.balls[4].state.rvw[0] = wiggle(
            np.array([0, 2 * a * r, self.radius]), self.spacer
        )
        self.balls[5].state.rvw[0] = wiggle(
            np.array([+2 * r, 2 * a * r, self.radius]), self.spacer
        )

        # row 4
        self.balls[6].state.rvw[0] = wiggle(
            np.array([-3 * r, 3 * a * r, self.radius]), self.spacer
        )
        self.balls[7].state.rvw[0] = wiggle(
            np.array([-1 * r, 3 * a * r, self.radius]), self.spacer
        )
        self.balls[8].state.rvw[0] = wiggle(
            np.array([+1 * r, 3 * a * r, self.radius]), self.spacer
        )
        self.balls[9].state.rvw[0] = wiggle(
            np.array([+3 * r, 3 * a * r, self.radius]), self.spacer
        )

        # row 5
        self.balls[10].state.rvw[0] = wiggle(
            np.array([-4 * r, 4 * a * r, self.radius]), self.spacer
        )
        self.balls[11].state.rvw[0] = wiggle(
            np.array([-2 * r, 4 * a * r, self.radius]), self.spacer
        )
        self.balls[12].state.rvw[0] = wiggle(
            np.array([+0 * r, 4 * a * r, self.radius]), self.spacer
        )
        self.balls[13].state.rvw[0] = wiggle(
            np.array([+2 * r, 4 * a * r, self.radius]), self.spacer
        )
        self.balls[14].state.rvw[0] = wiggle(
            np.array([+4 * r, 4 * a * r, self.radius]), self.spacer
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
