from typing import Callable, Optional

import attrs
import numpy as np

import pooltool.ai.aim as aim
from pooltool.ai.action import Action
from pooltool.game.ruleset.datatypes import Ruleset
from pooltool.game.ruleset.utils import StateProbe, get_lowest_ball
from pooltool.system.datatypes import System


@attrs.define
class AimNaiveAI:
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

        lowest_ball = get_lowest_ball(system, when=StateProbe.CURRENT)
        action.phi = aim.at_ball(system, lowest_ball.id, cut=np.random.uniform(-70, 70))

        return action

    def apply(self, system: System, action: Action) -> None:
        action.apply(system.cue)
