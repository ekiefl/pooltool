from typing import Callable, Optional

import attrs
import numpy as np

from pooltool.ai.action import Action
from pooltool.ai.pot import PottingConfig
from pooltool.game.datatypes import GameType
from pooltool.game.ruleset import get_ruleset
from pooltool.game.ruleset.datatypes import Ruleset
from pooltool.ptmath import wiggle
from pooltool.system.datatypes import System

AIMER = PottingConfig.default()

SUPPORTED_GAMETYPES = {
    GameType.NINEBALL,
}


@attrs.define
class AimPocketAI:
    game: Ruleset = attrs.field()
    dphi: float = attrs.field(default=0)

    @game.validator  # type: ignore
    def _game_supported(self, _, val) -> None:
        supports = [get_ruleset(gametype) for gametype in SUPPORTED_GAMETYPES]
        assert any(isinstance(val, cls) for cls in supports), f"{type(val)} unsupported"

    def decide(
        self,
        system: System,
        game: Ruleset,
        callback: Optional[Callable[[Action], None]] = None,
    ) -> Action:
        action = Action(
            V0=np.random.uniform(0.5, 4),
            phi=np.random.uniform(0, 360),
            theta=np.random.uniform(0, 0),
            a=np.random.uniform(-0.5, 0.5),
            b=np.random.uniform(-0.5, 0.5),
        )

        cue_ball = system.balls["cue"]
        object_ball = system.balls[game.shot_constraints.hittable[0]]

        pocket = AIMER.choose_pocket(cue_ball, object_ball, system.table, None)
        if pocket is None:
            # No pocket is viable, just pick any pocket :(
            pocket = list(system.table.pockets.values())[0]

        action.phi = AIMER.calculate_angle(
            cue_ball,
            object_ball,
            system.table,
            pocket,
        )

        action.phi = wiggle(action.phi, self.dphi)

        return action

    def apply(self, system: System, action: Action) -> None:
        action.apply(system.cue)
