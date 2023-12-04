from pooltool.game.datatypes import GameType
from pooltool.game.ruleset.datatypes import Ruleset
from pooltool.game.ruleset.eight_ball import EightBall
from pooltool.game.ruleset.nine_ball import NineBall
from pooltool.game.ruleset.sandbox import SandBox
from pooltool.game.ruleset.snooker import Snooker
from pooltool.game.ruleset.three_cushion import ThreeCushion
from pooltool.game.ruleset.one_rail import OneRail

_ruleset_classes = {
    GameType.NINEBALL: NineBall,
    GameType.EIGHTBALL: EightBall,
    GameType.THREECUSHION: ThreeCushion,
    GameType.SNOOKER: Snooker,
    GameType.SANDBOX: SandBox,
    GameType.ONERAIL: OneRail,
}


def get_ruleset(game: GameType) -> Ruleset:
    return _ruleset_classes[game]()
