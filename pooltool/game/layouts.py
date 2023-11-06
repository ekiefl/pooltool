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
from pooltool.system.datatypes import Balls
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


class Jump:
    @staticmethod
    def LEFT(quantity: int = 1) -> List[Dir]:
        return [Dir.LEFT] * quantity

    @staticmethod
    def RIGHT(quantity: int = 1) -> List[Dir]:
        return [Dir.RIGHT] * quantity

    @staticmethod
    def UP(quantity: int = 1) -> List[Dir]:
        return [Dir.UP] * quantity

    @staticmethod
    def DOWN(quantity: int = 1) -> List[Dir]:
        return [Dir.DOWN] * quantity

    @staticmethod
    def UPLEFT(quantity: int = 1) -> List[Dir]:
        return [Dir.UPLEFT] * quantity

    @staticmethod
    def UPRIGHT(quantity: int = 1) -> List[Dir]:
        return [Dir.UPRIGHT] * quantity

    @staticmethod
    def DOWNRIGHT(quantity: int = 1) -> List[Dir]:
        return [Dir.DOWNRIGHT] * quantity

    @staticmethod
    def DOWNLEFT(quantity: int = 1) -> List[Dir]:
        return [Dir.DOWNLEFT] * quantity

    @staticmethod
    def eval(translations: List[Dir], radius: float) -> Tuple[float, float]:
        mapping = Dir.translation_map
        assert isinstance(mapping, dict)

        dx, dy = 0, 0

        for direction in translations:
            i, j = mapping[direction]
            dx += i * radius
            dy += j * radius

        return dx, dy


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

    loc: List[Dir]
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


def _get_anchor_translation(pos: Pos) -> Tuple[Tuple[float, float], List[Dir]]:
    """Traverse the position's parent hierarchy until the anchor is found"""

    translation_from_anchor: List[Dir] = []
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
) -> Balls:
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

    balls: Balls = {}

    ball_ids = _get_ball_ids(blueprint)

    for ball in blueprint:
        (x, y), translation = _get_anchor_translation(ball)

        x *= table.w
        y *= table.l

        dx, dy = Jump.eval(translation, radius)

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


def get_nine_ball_rack(*args, **kwargs) -> Balls:
    others = {"2", "3", "4", "5", "6", "7", "8"}

    row1 = [
        (anchor := BallPos([], (0.5, 0.77), {"1"})),
    ]

    row2 = [
        (anchor := BallPos(Jump.UPLEFT(), anchor, others)),
        BallPos(Jump.RIGHT(), anchor, others),
    ]

    row3 = [
        (anchor := BallPos(Jump.UPLEFT(), anchor, others)),
        BallPos(Jump.RIGHT(1), anchor, {"9"}),
        BallPos(Jump.RIGHT(2), anchor, others),
    ]

    row4 = [
        (anchor := BallPos(Jump.UPRIGHT(), anchor, others)),
        BallPos(Jump.RIGHT(), anchor, others),
    ]

    row5 = [
        BallPos(Jump.UPRIGHT(), anchor, others),
    ]

    cue = BallPos([], (0.85, 0.23), {"cue"})

    blueprint = row1 + row2 + row3 + row4 + row5 + [cue]
    return _get_rack(blueprint, *args, **kwargs)


def get_eight_ball_rack(*args, **kwargs) -> Balls:
    stripes = {"9", "10", "11", "12", "13", "14", "15"}
    solids = {"1", "2", "3", "4", "5", "6", "7"}

    row1 = [
        (anchor := BallPos([], (0.5, 0.77), solids)),
    ]

    row2 = [
        (anchor := BallPos(Jump.UPLEFT(), anchor, stripes)),
        BallPos(Jump.RIGHT(), anchor, solids),
    ]

    row3 = [
        (anchor := BallPos(Jump.UPLEFT(), anchor, solids)),
        BallPos(Jump.RIGHT(1), anchor, {"8"}),
        BallPos(Jump.RIGHT(2), anchor, stripes),
    ]

    row4 = [
        (anchor := BallPos(Jump.UPLEFT(), anchor, stripes)),
        BallPos(Jump.RIGHT(1), anchor, solids),
        BallPos(Jump.RIGHT(2), anchor, stripes),
        BallPos(Jump.RIGHT(3), anchor, solids),
    ]

    row5 = [
        (anchor := BallPos(Jump.UPLEFT(), anchor, solids)),
        BallPos(Jump.RIGHT(1), anchor, stripes),
        BallPos(Jump.RIGHT(2), anchor, stripes),
        BallPos(Jump.RIGHT(3), anchor, solids),
        BallPos(Jump.RIGHT(4), anchor, stripes),
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
        (anchor := BallPos(Jump.UP(), (0.5, 0.75), red_ids)),
    ]

    row2 = [
        (anchor := BallPos(Jump.UPLEFT(), anchor, red_ids)),
        BallPos(Jump.RIGHT(), anchor, red_ids),
    ]

    row3 = [
        (anchor := BallPos(Jump.UPLEFT(), anchor, red_ids)),
        BallPos(Jump.RIGHT(1), anchor, red_ids),
        BallPos(Jump.RIGHT(2), anchor, red_ids),
    ]

    row4 = [
        (anchor := BallPos(Jump.UPLEFT(), anchor, red_ids)),
        BallPos(Jump.RIGHT(1), anchor, red_ids),
        BallPos(Jump.RIGHT(2), anchor, red_ids),
        BallPos(Jump.RIGHT(3), anchor, red_ids),
    ]

    row5 = [
        (anchor := BallPos(Jump.UPLEFT(), anchor, red_ids)),
        BallPos(Jump.RIGHT(1), anchor, red_ids),
        BallPos(Jump.RIGHT(2), anchor, red_ids),
        BallPos(Jump.RIGHT(3), anchor, red_ids),
        BallPos(Jump.RIGHT(4), anchor, red_ids),
    ]

    blueprint = colors + row1 + row2 + row3 + row4 + row5
    return _get_rack(blueprint, *args, **kwargs)


_game_rack_map: Dict[str, Callable[[Table, Optional[BallParams], float], Balls]] = {
    GameType.NINEBALL: get_nine_ball_rack,
    GameType.EIGHTBALL: get_eight_ball_rack,
    GameType.THREECUSHION: get_three_cushion_rack,
    GameType.SNOOKER: get_snooker_rack,
    GameType.SANDBOX: get_nine_ball_rack,
}


def get_rack(
    game_type: GameType,
    table: Table,
    params: Optional[BallParams],
    spacing_factor: float,
) -> Balls:
    return _game_rack_map[game_type](table, params, spacing_factor)
