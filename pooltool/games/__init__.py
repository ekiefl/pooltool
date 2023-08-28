import pooltool.ani as ani
from pooltool.games.eight_ball import EightBall
from pooltool.games.nine_ball import NineBall
from pooltool.games.sandbox import Sandbox
from pooltool.games.three_cushion import ThreeCushion
from pooltool.games.snooker import Snooker

game_classes = {
    ani.options_sandbox: Sandbox,
    ani.options_9_ball: NineBall,
    ani.options_8_ball: EightBall,
    ani.options_3_cushion: ThreeCushion,
    ani.options_snooker: Snooker,
}
