from typing import Callable, Optional

import attrs

from pooltool.ai.datatypes import Action
from pooltool.ai.potting import PottingConfig
from pooltool.ai.potting.simple import calc_potting_angle, pick_best_pot
from pooltool.ai.utils import random_params
from pooltool.game.datatypes import GameType
from pooltool.game.ruleset import get_ruleset
from pooltool.game.ruleset.datatypes import Ruleset
from pooltool.game.ruleset.utils import StateProbe, get_lowest_ball
from pooltool.system.datatypes import System

SUPPORTED_GAMETYPES = {
    GameType.NINEBALL,
}

AIMER = PottingConfig(
    calculate_angle=calc_potting_angle,
    choose_pocket=pick_best_pot,
)


@attrs.define
class UnintelligentAI:
    game: Ruleset = attrs.field()

    @game.validator  # type: ignore
    def _game_supported(self, _, value) -> None:
        supported = [get_ruleset(gametype) for gametype in SUPPORTED_GAMETYPES]
        assert any(
            isinstance(value, cls) for cls in supported
        ), f"{type(value)} unsupported gametype"

    def decide(
        self,
        system: System,
        _: Ruleset,
        callback: Optional[Callable[[Action], None]] = None,
    ) -> Action:
        cue_ball = system.balls[system.cue.cue_ball_id]
        lowest_ball = get_lowest_ball(system, when=StateProbe.CURRENT)
        pockets = list(system.table.pockets.values())

        action = random_params()
        action.phi = AIMER.calculate_angle(
            cue_ball,
            lowest_ball,
            AIMER.choose_pocket(cue_ball, lowest_ball, pockets),
        )

        if callback is not None:
            callback(action)

        return action

    def apply(self, system: System, action: Action) -> None:
        action.apply(system.cue)
        system.strike()
