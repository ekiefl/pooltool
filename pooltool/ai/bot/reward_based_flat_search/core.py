from typing import Callable, List, Optional

import attrs

from pooltool.ai.action import Action
from pooltool.ai.bot.reward_based_flat_search.action_generation import (
    apply_phi_to_action,
    get_best_aiming_phi,
    get_break_action,
    random_action,
)
from pooltool.ai.datatypes import State
from pooltool.ai.reward.nine_ball import RewardPointBased
from pooltool.evolution.event_based.simulate import simulate
from pooltool.game.datatypes import GameType
from pooltool.game.ruleset import get_ruleset
from pooltool.game.ruleset.datatypes import Ruleset
from pooltool.system.datatypes import System

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
    state.system.strike()
    simulate(state.system, inplace=True)
    state.game.process_shot(state.system)
    state.game.advance(state.system)


Callback = Callable[[Action], None]


@attrs.define
class RewardBasedFlatSearch:
    game: Ruleset = attrs.field()
    rewarder: RewardPointBased = attrs.field(default=RewardPointBased())
    iterations: int = attrs.field(default=25)

    @game.validator  # type: ignore
    def _game_supported(self, _, value) -> None:
        supported = [get_ruleset(gametype) for gametype in SUPPORTED_GAMETYPES]
        assert any(
            isinstance(value, cls) for cls in supported
        ), f"{type(value)} unsupported gametype"

    def decide_break(
        self, system: System, game: Ruleset, callback: Optional[Callback] = None
    ):
        """Decide on a break action"""

        assert game.shot_number == 0

        action = get_break_action(system, game)

        if callback is not None:
            callback(action)

        return action

    def decide_pot(
        self, system: System, game: Ruleset, callback: Optional[Callback] = None
    ):
        """Decide on a potting action"""

        potting_phi = get_best_aiming_phi(system, game)

        results: List[Result] = []
        for i in range(self.iterations):
            state = State(system.copy(), game.copy())

            action = apply_phi_to_action(potting_phi, 0.0, random_action())
            simulate_action(state, action)

            reward = self.rewarder.calc(state, debug=True)
            results.append(Result(i, action, reward))

            if callback is not None and (i % 1) == 0:
                callback(best_result(results).action)

        return best_result(results).action

    def decide_safety(
        self, system: System, game: Ruleset, callback: Optional[Callback] = None
    ):
        """Decide on a safety action"""
        raise NotImplementedError()

    def decide(
        self, system: System, game: Ruleset, callback: Optional[Callback] = None
    ) -> Action:
        """Core decision making method

        This decides whether to play a break shot, a potting shot, or a safety shot, and
        then returns an action.
        """
        if game.shot_number == 0:
            return self.decide_break(system, game, callback)

        viable_pots = True
        if viable_pots:
            return self.decide_pot(system, game, callback)

        return self.decide_safety(system, game, callback)

    def apply(self, system: System, action: Action) -> None:
        action.apply(system.cue)
        system.strike()
