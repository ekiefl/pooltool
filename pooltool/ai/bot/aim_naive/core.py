from typing import Callable, Optional

from pooltool.ai.action import Action
from pooltool.game.ruleset.datatypes import Ruleset
from pooltool.game.ruleset.utils import StateProbe, get_lowest_ball
from pooltool.ptmath import wiggle
from pooltool.system.datatypes import System


class AimNaiveAI:
    def decide(
        self,
        system: System,
        game: Ruleset,
        callback: Optional[Callable[[Action], None]] = None,
    ) -> Action:
        lowest_ball = get_lowest_ball(system, when=StateProbe.CURRENT)

        # Shortcoming of the System dataclass API, here. I have a System method
        # `aim_at_ball` that sets the cue's parameters to aim at the ball with a desired
        # cut angle. But `decide` is not supposed to set the cue state, it's just
        # supposed to return the action. So to get around this, I store the cue state,
        # call `aim_at_ball`, get the action, then set the cue state back to what it was
        # originally.
        original_action = Action.from_cue(system.cue)
        system.aim_at_ball(lowest_ball.id)
        action = Action.from_cue(system.cue)
        action.phi = wiggle(action.phi, 2)
        original_action.apply(system.cue)

        return action

    def apply(self, system: System, action: Action) -> None:
        action.apply(system.cue)
