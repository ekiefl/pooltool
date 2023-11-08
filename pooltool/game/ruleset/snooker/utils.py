#! /usr/bin/env python

from __future__ import annotations

from typing import Dict, Tuple

from pooltool.game.ruleset.datatypes import ShotConstraints
from pooltool.game.ruleset.utils import (
    get_ball_ids_on_table,
    get_pocketed_ball_ids,
    get_pocketed_ball_ids_during_shot,
    is_target_group_hit_first,
)
from pooltool.system.datatypes import System
from pooltool.utils.strenum import StrEnum, auto


class BallGroup(StrEnum):
    REDS = auto()
    COLORS = auto()

    @property
    def balls(self) -> Tuple[str, ...]:
        """Return the ball IDs associated to a BallGroup"""
        return _group_to_balls_dict[self]

    def next(self, shot: System) -> BallGroup:
        """Get next player's ball-group"""
        if are_reds_done(shot):
            return BallGroup.COLORS

        return BallGroup.REDS

    def cont(self, shot: System, constraints: ShotConstraints) -> BallGroup:
        """Get the same player's ball-group for next shot"""
        if are_reds_done(shot):
            return BallGroup.COLORS

        curr_group = BallGroup.get(constraints.hittable)
        return BallGroup.COLORS if curr_group is BallGroup.REDS else BallGroup.REDS

    @classmethod
    def get(cls, balls: Tuple[str, ...]) -> BallGroup:
        return _balls_to_group_dict[balls]


_group_to_balls_dict: Dict[BallGroup, Tuple[str, ...]] = {
    BallGroup.REDS: tuple(f"red_{i:02d}" for i in range(1, 16)),
    BallGroup.COLORS: ("yellow", "green", "brown", "blue", "pink", "black"),
}

_balls_to_group_dict: Dict[Tuple[str, ...], BallGroup] = {
    v: k for k, v in _group_to_balls_dict.items()
}


def are_reds_done(shot: System) -> bool:
    return all(ball in get_pocketed_ball_ids(shot) for ball in BallGroup.REDS.balls)


def on_final_black(shot: System) -> bool:
    balls_on_table_t0 = get_ball_ids_on_table(shot, at_start=True)
    return (
        len(balls_on_table_t0) == 2
        and "white" in balls_on_table_t0
        and "black" in balls_on_table_t0
    )


def get_on_balls(constraints: ShotConstraints) -> Tuple[str, ...]:
    """Get all balls that are 'on'

    If player is on reds, all reds are on. If player is on colors, the called color is
    on. This is different than constraints.hittable, which states which group of balls
    the player _could_ hit, whereas `_get_on_balls` says which balls the player has
    _chosen_ to hit.
    """
    group = BallGroup.get(constraints.hittable)

    if group is BallGroup.REDS:
        return BallGroup.REDS.balls

    assert constraints.call_shot, "If you're playing colors, it must be call shot"
    assert constraints.ball_call is not None, "Ball must be called before _get_on_balls"

    return (constraints.ball_call,)


def is_off_ball_pocketed(shot: System, constraints: ShotConstraints) -> bool:
    on_balls = get_on_balls(constraints)
    return bool(len(get_pocketed_ball_ids_during_shot(shot, set(on_balls) | {"white"})))


def is_off_ball_hit_first(shot: System, constraints: ShotConstraints) -> bool:
    return not is_target_group_hit_first(shot, get_on_balls(constraints))


POINTS = {
    "white": -4,
    "yellow": 2,
    "green": 3,
    "brown": 4,
    "blue": 5,
    "pink": 6,
    "black": 7,
}
POINTS.update({red: 1 for red in BallGroup.REDS.balls})
