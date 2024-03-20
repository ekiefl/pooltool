#! /usr/bin/env python

from __future__ import annotations

from typing import Iterable, List, Tuple

from pooltool.ruleset.datatypes import ShotConstraints
from pooltool.ruleset.snooker.balls import (
    BallGroup,
    ball_info,
    ball_infos,
    ball_infos_dict,
)
from pooltool.ruleset.utils import (
    get_ball_ids_on_table,
    get_pocketed_ball_ids_during_shot,
    is_ball_pocketed,
    is_target_group_hit_first,
)
from pooltool.system.datatypes import System
from pooltool.utils.strenum import StrEnum, auto


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
    """Have all reds been sunk (by end of shot)

    Better to calculate if reds are on the table, rather than if all reds are in the
    pocket, since some variants of snooker use less reds.
    """
    return not any(
        ball in BallGroup.REDS.balls
        for ball in get_ball_ids_on_table(shot, at_start=False)
    )


class GamePhase(StrEnum):
    """Which phase is the game currently in?

    Attributes:
        ALTERNATING:
            There are reds on the table and players alternate between
            potting reds and potting colors.
        SEQUENTIAL:
            Means the colors must be potted in order
    """

    SEQUENTIAL = auto()
    ALTERNATING = auto()


def game_phase(shot: System, legal: bool) -> GamePhase:
    if not are_reds_done(shot):
        return GamePhase.ALTERNATING

    return (
        GamePhase.ALTERNATING
        if is_transition_to_sequential_mode(shot, legal)
        else GamePhase.SEQUENTIAL
    )


def is_transition_to_sequential_mode(shot: System, legal: bool) -> bool:
    """Returns whether game is transitioning from alternating phase to sequential phase

    Inbetween GamePhase.ALTERNATING and GamePhase.SEQUENTIAL, there is a _potential_
    transitional shot, which occurs when the player legally pots the last red, and gets
    their pick of any color ball before sequential mode begins, even though there are no
    reds on the table. This function returns whether or not that transitional shot is
    about to occur by counting the number of reds on the table before and after the
    shot, as well as wheher or not the player's shot was legal.
    """
    red_sunk = any(
        ball_id.startswith("red_")
        for ball_id in get_pocketed_ball_ids_during_shot(shot)
    )

    return are_reds_done(shot) and red_sunk and legal


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
    on[1]. Which ball(s) is/are on is different than constraints.hittable, which states
    the group of balls the player _could_ hit, whereas `get_on_balls` says which balls
    the player has _chosen_ to hit. Sometimes these are the same.

    [1] If the player is shooting in sequential mode, whereby players pot the colored
    balls in order, there is no need to call the ball because the on ball is the lowest
    value colored on the table.
    """
    if (
        BallGroup.get(constraints.hittable) is BallGroup.COLORS
        and len(constraints.hittable) > 1
    ):
        # Player is in alternate mode and on colors, meaning they must elect a ball
        assert constraints.call_shot, "Call shot must be true in this instance"
        assert constraints.ball_call is not None, "Ball must be called by this point"
        return (constraints.ball_call,)

    return constraints.hittable


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


def get_color_balls_to_be_potted(
    shot: System, legal: bool, ball_call: str
) -> List[str]:
    """Returns all color balls that still need to be potted"""
    color_balls_to_be_potted = [
        ball_id
        for ball_id, info in ball_infos_dict.items()
        if info.color and info.points >= ball_info(get_lowest_pottable(shot)).points
    ]

    if not legal and is_ball_pocketed(shot, ball_call):
        # If player potted on-ball illegally, must be re-spotted and re-potted
        color_balls_to_be_potted.append(ball_call)

    return color_balls_to_be_potted


def get_foul_points(offending_balls: Iterable[str]) -> int:
    """Return the number of points for the foul"""
    return max(4, max(ball_info(ball_id).points for ball_id in offending_balls))
