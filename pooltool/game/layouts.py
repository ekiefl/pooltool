#! /usr/bin/env python

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from collections import Counter
from typing import Callable, Dict, List, Optional, Set, Tuple, Union

import attrs
import numpy as np
from numpy.typing import NDArray

from pooltool.game.datatypes import GameType
from pooltool.objects.ball.datatypes import Ball, BallParams
from pooltool.objects.table.datatypes import Table
from pooltool.utils import classproperty
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

    @classproperty
    def translation_map(cls) -> Dict[Dir, Tuple[float, float]]:
        a = np.sqrt(3)
        return {
            Dir.LEFT: (-2, 0),
            Dir.RIGHT: (2, 0),
            Dir.UP: (0, 2),
            Dir.DOWN: (0, -2),
            Dir.UPRIGHT: (1, a),
            Dir.DOWNRIGHT: (1, -a),
            Dir.UPLEFT: (-1, a),
            Dir.DOWNLEFT: (-1, -a),
        }


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
    quantity: int = 1

    def eval(self, radius: float) -> Tuple[float, float]:
        mapping = Dir.translation_map
        assert isinstance(mapping, dict)
        delta_x, delta_y = mapping[self.direction]
        return delta_x * self.quantity * radius, delta_y * self.quantity * radius


@attrs.define
class Pos:
    """Defines a position relative to another position, or a 2D table coordinate

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


def _get_anchor_translation(pos: Pos) -> Tuple[Tuple[float, float], List[Trans]]:
    """Traverse the position's parent hierarchy until the anchor is found"""

    translation_from_anchor: List[Trans] = []
    translation_from_anchor.extend(pos.loc)

    parent = pos.relative_to

    while True:
        if isinstance(parent, tuple):
            return parent, translation_from_anchor

        translation_from_anchor.extend(parent.loc)
        parent = parent.relative_to


def _get_rack(
    blueprint: List[BallPos],
    table: Table,
    ball_params: Optional[BallParams] = None,
    spacing_factor: float = 1e-3,
    seed: Optional[int] = None,
) -> Dict[str, Ball]:
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
        spacing_factor:
            FIXME Get ChatGPT to explain this.
        seed:
            Set a seed for reproducibility. That's because getting a rack
            involves two random procedures. First, some ball positions can be
            satisfied with many different ball IDs. For example, in 9 ball, only
            the 1 ball and 9 ball are predetermined, the positions of the other
            balls are random. The second source of randomnness is from
            spacing_factor.

    Returns:
        balls:
            A dictionary mapping ball IDs to their respective Ball objects, with
            their absolute positions on the table.

    Notes:
    - The table dimensions are normalized such that the bottom-left corner is
      (0.0, 0.0) and the top-right corner is (1.0, 1.0).
    """

    if ball_params is None:
        ball_params = BallParams.default()

    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    ball_radius = ball_params.R
    radius = ball_radius * (1 + spacing_factor)

    balls: Dict[str, Ball] = {}

    ball_ids = _get_ball_ids(blueprint)

    for ball in blueprint:
        (x, y), translation = _get_anchor_translation(ball)

        x *= table.w
        y *= table.l

        for trans in translation:
            dx, dy = trans.eval(radius)
            x += dx
            y += dy

        x, y = _wiggle(x, y, ball_radius * spacing_factor)

        # Choose ball
        remaining = ball_ids.intersection(ball.ids)

        assert len(remaining), "Ball requirements of blueprint unsatisfiable"
        ball_id = random.choice(list(remaining))
        ball_ids.remove(ball_id)

        # Create ball
        balls[ball_id] = Ball.create(ball_id, xy=(x, y), **attrs.asdict(ball_params))

    return balls


def _wiggle(x: float, y: float, spacer: float) -> Tuple[float, float]:
    ang = 2 * np.pi * np.random.rand()
    rad = spacer * np.random.rand()

    return x + rad * np.cos(ang), y + rad * np.sin(ang)


GO_LEFT = Trans(Dir.LEFT, 1)
GO_RIGHT = Trans(Dir.RIGHT, 1)
GO_UP = Trans(Dir.UP, 1)
GO_DOWN = Trans(Dir.DOWN, 1)
GO_UPLEFT = Trans(Dir.UPLEFT, 1)
GO_UPRIGHT = Trans(Dir.UPRIGHT, 1)
GO_DOWNLEFT = Trans(Dir.DOWNLEFT, 1)
GO_DOWNRIGHT = Trans(Dir.DOWNRIGHT, 1)


def get_nine_ball_rack(*args, **kwargs) -> Dict[str, Ball]:
    others = {"2", "3", "4", "5", "6", "7", "8"}

    row1 = [
        (anchor := BallPos([], (0.5, 0.77), {"1"})),
    ]

    row2 = [
        (anchor := BallPos([GO_UPLEFT], anchor, others)),
        BallPos([GO_RIGHT], anchor, others),
    ]

    row3 = [
        (anchor := BallPos([GO_UPLEFT], anchor, others)),
        BallPos([GO_RIGHT], anchor, {"9"}),
        BallPos([GO_RIGHT] * 2, anchor, others),
    ]

    row4 = [
        (anchor := BallPos([GO_UPRIGHT], anchor, others)),
        BallPos([GO_RIGHT], anchor, others),
    ]

    row5 = [
        BallPos([GO_UPRIGHT], anchor, others),
    ]

    cue = BallPos([], (0.85, 0.23), {"cue"})

    blueprint = row1 + row2 + row3 + row4 + row5 + [cue]
    return _get_rack(blueprint, *args, **kwargs)


def get_eight_ball_rack(*args, **kwargs) -> Dict[str, Ball]:
    stripes = {"9", "10", "11", "12", "13", "14", "15"}
    solids = {"1", "2", "3", "4", "5", "6", "7"}

    row1 = [
        (anchor := BallPos([], (0.5, 0.77), solids)),
    ]

    row2 = [
        (anchor := BallPos([GO_UPLEFT], anchor, stripes)),
        BallPos([GO_RIGHT], anchor, solids),
    ]

    row3 = [
        (anchor := BallPos([GO_UPLEFT], anchor, solids)),
        BallPos([GO_RIGHT], anchor, {"8"}),
        BallPos([GO_RIGHT] * 2, anchor, stripes),
    ]

    row4 = [
        (anchor := BallPos([GO_UPLEFT], anchor, stripes)),
        BallPos([GO_RIGHT], anchor, solids),
        BallPos([GO_RIGHT] * 2, anchor, stripes),
        BallPos([GO_RIGHT] * 3, anchor, solids),
    ]

    row5 = [
        (anchor := BallPos([GO_UPLEFT], anchor, solids)),
        BallPos([GO_RIGHT], anchor, stripes),
        BallPos([GO_RIGHT] * 2, anchor, stripes),
        BallPos([GO_RIGHT] * 3, anchor, solids),
        BallPos([GO_RIGHT] * 4, anchor, stripes),
    ]

    # Cue ball
    cue = BallPos([], (0.6, 0.23), {"cue"})

    blueprint = row1 + row2 + row3 + row4 + row5 + [cue]
    return _get_rack(blueprint, *args, **kwargs)


def get_three_cushion_rack(*args, **kwargs):
    """A three cushion starting position (white to break)

    Based on https://www.3cushionbilliards.com/rules/106-official-us-billiard-association-rules-of-play
    """

    white = BallPos([], (0.62, 0.25), {"white"})
    yellow = BallPos([], (0.5, 0.25), {"yellow"})
    red = BallPos([], (0.5, 0.75), {"red"})

    return _get_rack([white, yellow, red], *args, **kwargs)


def get_snooker_rack(*args, **kwargs):
    colors = [
        BallPos([], (7 / 12, 0.2), {"white"}),
        BallPos([], (0.333, 0.2), {"yellow"}),
        BallPos([], (0.666, 0.2), {"green"}),
        BallPos([], (0.5, 0.2), {"brown"}),
        BallPos([], (0.5, 0.5), {"blue"}),
        BallPos([], (0.5, 10 / 11), {"black"}),
        BallPos([], (0.5, 0.75), {"pink"}),
    ]

    red_ids = set([f"red{i}" for i in range(1, 16)])

    row1 = [
        (anchor := BallPos([GO_UP], (0.5, 0.75), red_ids)),
    ]

    row2 = [
        (anchor := BallPos([GO_UPLEFT], anchor, red_ids)),
        BallPos([GO_RIGHT], anchor, red_ids),
    ]

    row3 = [
        (anchor := BallPos([GO_UPLEFT], anchor, red_ids)),
        BallPos([GO_RIGHT], anchor, red_ids),
        BallPos([GO_RIGHT] * 2, anchor, red_ids),
    ]

    row4 = [
        (anchor := BallPos([GO_UPLEFT], anchor, red_ids)),
        BallPos([GO_RIGHT], anchor, red_ids),
        BallPos([GO_RIGHT] * 2, anchor, red_ids),
        BallPos([GO_RIGHT] * 3, anchor, red_ids),
    ]

    row5 = [
        (anchor := BallPos([GO_UPLEFT], anchor, red_ids)),
        BallPos([GO_RIGHT], anchor, red_ids),
        BallPos([GO_RIGHT] * 2, anchor, red_ids),
        BallPos([GO_RIGHT] * 3, anchor, red_ids),
        BallPos([GO_RIGHT] * 4, anchor, red_ids),
    ]

    blueprint = colors + row1 + row2 + row3 + row4 + row5
    return _get_rack(blueprint, *args, **kwargs)


_game_rack_map: Dict[
    str, Callable[[Table, Optional[BallParams], float], Dict[str, Ball]]
] = {
    GameType.NINEBALL: get_nine_ball_rack,
    GameType.EIGHTBALL: get_eight_ball_rack,
    GameType.THREECUSHION: get_three_cushion_rack,
    GameType.SNOOKER: get_snooker_rack,
}


def get_rack(
    game_type: GameType,
    table: Table,
    params: Optional[BallParams],
    spacing_factor: float,
) -> Dict[str, Ball]:
    return _game_rack_map[game_type](table, params, spacing_factor)
