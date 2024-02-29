from typing import Type

from pooltool.game.datatypes import GameType
from pooltool.game.ruleset.datatypes import Ruleset
from pooltool.game.ruleset.eight_ball import _EightBall
from pooltool.game.ruleset.nine_ball import _NineBall
from pooltool.game.ruleset.sandbox import _SandBox
from pooltool.game.ruleset.snooker import _Snooker
from pooltool.game.ruleset.sum_to_three import _SumToThree
from pooltool.game.ruleset.three_cushion import _ThreeCushion

_ruleset_classes = {
    GameType.NINEBALL: _NineBall,
    GameType.EIGHTBALL: _EightBall,
    GameType.THREECUSHION: _ThreeCushion,
    GameType.SNOOKER: _Snooker,
    GameType.SANDBOX: _SandBox,
    GameType.SUMTOTHREE: _SumToThree,
}


def get_ruleset(game: GameType) -> Type[Ruleset]:
    """Retrieve a ruleset class

    Args:
        game:
            The game type.

    Returns:
        Type[Ruleset]:
            An uninitialized class object representing a game.
    """
    return _ruleset_classes[game]
