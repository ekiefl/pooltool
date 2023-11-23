from typing import Callable, Optional

import numpy as np

from pooltool.ai.action import Action
from pooltool.game.ruleset.datatypes import Ruleset
from pooltool.system.datatypes import System


class WorstAI:
    def decide(
        self,
        system: System,
        game: Ruleset,
        callback: Optional[Callable[[Action], None]] = None,
    ) -> Action:
        return Action(
            V0=np.random.uniform(0.5, 4),
            phi=np.random.uniform(0, 360),
            theta=np.random.uniform(0, 0),
            a=np.random.uniform(-0.5, 0.5),
            b=np.random.uniform(-0.5, 0.5),
        )

    def apply(self, system: System, action: Action) -> None:
        action.apply(system.cue)
