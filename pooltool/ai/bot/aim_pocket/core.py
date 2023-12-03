from typing import Callable, List, Optional

import attrs
import numpy as np

from pooltool.ai.action import Action
from pooltool.ai.datatypes import State
from pooltool.ai.pot import PottingConfig
from pooltool.ai.reward.datatypes import Rewarder
from pooltool.ai.reward.nine_ball.potting.point_based.core import RewardPointBased
from pooltool.evolution.event_based.simulate import simulate
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
class Result:
    idx: int
    action: Action
    reward: float


def best_result(results: List[Result]) -> Result:
    return max(results, key=lambda result: result.reward)


def simulate_action(state: State, action: Action) -> None:
    action.apply(state.system.cue)
    simulate(state.system, inplace=True)
    state.game.process_shot(state.system)
    state.game.advance(state.system)


def get_action(state: State, dphi: float) -> Action:
    action = Action(
        V0=np.random.uniform(0.5, 4),
        phi=np.random.uniform(0, 360),
        theta=np.random.uniform(0, 0),
        a=np.random.uniform(-0.5, 0.5),
        b=np.random.uniform(-0.5, 0.5),
    )

    cue_ball = state.system.balls["cue"]
    object_ball = state.system.balls[state.game.shot_constraints.hittable[0]]

    pocket = AIMER.choose_pocket(state.system, cue_ball)
    if pocket is None:
        # No pocket is viable, just pick any pocket :(
        pocket = list(state.system.table.pockets.values())[0]

    action.phi = AIMER.calculate_angle(
        cue_ball,
        object_ball,
        state.system.table,
        pocket,
    )

    action.phi = wiggle(action.phi, dphi)
    return action


@attrs.define
class AimPocketAI:
    game: Ruleset = attrs.field()
    rewarder: Rewarder = attrs.field(default=RewardPointBased())
    iterations: int = attrs.field(default=1)
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
        results: List[Result] = []
        for i in range(self.iterations):
            state = State(system.copy(), game.copy())
            action = get_action(state, self.dphi)
            simulate_action(state, action)

            reward = self.rewarder.calc(state)
            results.append(Result(i, action, reward))

            if callback is not None and (i % 1) == 0:
                callback(best_result(results).action)

        return best_result(results).action

    def apply(self, system: System, action: Action) -> None:
        action.apply(system.cue)
