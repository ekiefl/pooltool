import pooltool.ani as ani
from pooltool.game.ruleset.eight_ball import EightBall
from pooltool.game.ruleset.nine_ball import NineBall
from pooltool.game.ruleset.sandbox import Sandbox
from pooltool.game.ruleset.snooker import Snooker
from pooltool.game.ruleset.three_cushion import ThreeCushion

game_classes = {
    ani.options_sandbox: Sandbox,
    ani.options_9_ball: NineBall,
    ani.options_8_ball: EightBall,
    ani.options_3_cushion: ThreeCushion,
    ani.options_snooker: Snooker,
}
