"""Ruleset logic"""

from pooltool.game.datatypes import GameType
from pooltool.ruleset.datatypes import (
    AIPlayer,
    BallInHandOptions,
    Player,
    Ruleset,
    ShotConstraints,
    ShotInfo,
)
from pooltool.ruleset.eight_ball import _EightBall
from pooltool.ruleset.nine_ball import _NineBall
from pooltool.ruleset.sandbox import _RulelessMode
from pooltool.ruleset.snooker import _Snooker
from pooltool.ruleset.sum_to_three import _SumToThree
from pooltool.ruleset.three_cushion import _ThreeCushion
from pooltool.ruleset.utils import (
    balls_that_hit_cushion,
    get_ball_ids_on_table,
    get_highest_ball,
    get_id_of_first_ball_hit,
    get_lowest_ball,
    get_pocketed_ball_ids,
    get_pocketed_ball_ids_during_shot,
    is_ball_hit,
    is_ball_pocketed,
    is_ball_pocketed_in_pocket,
    is_lowest_hit_first,
    is_numbered_ball_pocketed,
    is_shot_called_if_required,
    is_target_group_hit_first,
    respot,
)

_ruleset_classes = {
    GameType.NINEBALL: _NineBall,
    GameType.EIGHTBALL: _EightBall,
    GameType.THREECUSHION: _ThreeCushion,
    GameType.SNOOKER: _Snooker,
    GameType.SUMTOTHREE: _SumToThree,
}


def get_ruleset(game: GameType, enforce_rules: bool = True) -> type[Ruleset]:
    """Retrieve a ruleset class

    Args:
        game:
            The game type.
        enforce_rules:
            Whether to enforce game rules. If False, returns ruleless mode.

    Returns:
        Type[Ruleset]:
            An uninitialized class object representing a game.
    """
    if not enforce_rules:
        return _RulelessMode
    return _ruleset_classes[game]


__all__ = [
    "AIPlayer",
    "Player",
    "BallInHandOptions",
    "ShotConstraints",
    "ShotInfo",
    "Ruleset",
    "get_ruleset",
    "get_pocketed_ball_ids",
    "get_pocketed_ball_ids_during_shot",
    "get_id_of_first_ball_hit",
    "is_ball_pocketed",
    "is_ball_pocketed_in_pocket",
    "is_target_group_hit_first",
    "respot",
    "get_ball_ids_on_table",
    "get_lowest_ball",
    "get_highest_ball",
    "is_lowest_hit_first",
    "balls_that_hit_cushion",
    "is_ball_hit",
    "is_numbered_ball_pocketed",
    "is_shot_called_if_required",
]
