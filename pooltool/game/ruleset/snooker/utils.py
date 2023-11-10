#! /usr/bin/env python

from __future__ import annotations

from typing import Iterable, List, Tuple

from pooltool.game.ruleset.datatypes import ShotConstraints
from pooltool.game.ruleset.snooker.balls import (
    BallGroup,
    ball_info,
    ball_infos,
    ball_infos_dict,
)
from pooltool.game.ruleset.utils import (
    get_ball_ids_on_table,
    get_pocketed_ball_ids,
    get_pocketed_ball_ids_during_shot,
    is_target_group_hit_first,
)
from pooltool.system.datatypes import System
from pooltool.utils.strenum import StrEnum


class Reason(StrEnum):
    NONE = ""
    CUE_POCKETED = "Cue ball in pocket!"
    NO_BALL_HIT = "No ball contacted!"
    OFF_BALL_HIT_FIRST = "First contact made with a ball that's not on!"
    OFF_BALL_POCKETED = "Pocketed a ball that's not on!"


def get_next_player_ball_group(shot: System) -> BallGroup:
    """Get next player's ball-group"""
    if are_reds_done(shot):
        return BallGroup.COLORS

    return BallGroup.REDS


def get_continued_player_ball_group(
    shot: System, constraints: ShotConstraints
) -> BallGroup:
    """Get the same player's ball-group for next shot"""
    if are_reds_done(shot):
        return BallGroup.COLORS

    curr_group = BallGroup.get(constraints.hittable)
    return BallGroup.COLORS if curr_group is BallGroup.REDS else BallGroup.REDS


def are_reds_done(shot: System) -> bool:
    """Have all reds been sunk (by end of shot)"""
    return all(ball in get_pocketed_ball_ids(shot) for ball in BallGroup.REDS.balls)


def is_alternate_mode(shot: System, legal: bool) -> bool:
    if not are_reds_done(shot):
        return True

    return is_transition_to_sequential_mode(shot, legal)


def is_transition_to_sequential_mode(shot: System, legal: bool) -> bool:
    """Returns whether game is transitioning from alternate to sequential mode

    - Alternate mode means there are reds on the table and players alternate between
      potting reds and potting colors.

    - Sequential mode means the colors must be potted in order

    Inbetween these two modes, there is a _potential_ transitional shot, which occurs
    when the player legally pots the last red, and gets their pick of any color ball
    before sequential mode begins, even though there are no reds on the table. This
    function returns whether or not that transitional shot is about to occur by counting
    the number of reds on the table before and after the shot, as well as wheher or not
    the player's shot was legal.
    """
    if legal:
        return False

    red_sunk = any(
        ball_id.startswith("red_")
        for ball_id in get_pocketed_ball_ids_during_shot(shot)
    )

    if are_reds_done(shot) and red_sunk:
        return True

    return False


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
    return not is_target_group_hit_first(shot, get_on_balls(constraints), cue="white")


def get_lowest_pottable(shot: System) -> str:
    ball_ids = get_ball_ids_on_table(shot, at_start=False)
    return min(
        [info for info in ball_infos(ball_ids).values() if info.color],
        key=lambda info: info.points,
    ).id


def get_higher_value_color_balls(shot: System) -> List[str]:
    return [
        ball_id
        for ball_id, info in ball_infos_dict.items()
        if info.color and info.points >= ball_info(get_lowest_pottable(shot)).points
    ]


def get_foul_points(offending_balls: Iterable[str]) -> int:
    """Return the number of points for the foul"""
    return max(4, max(ball_info(ball_id).points for ball_id in offending_balls))
