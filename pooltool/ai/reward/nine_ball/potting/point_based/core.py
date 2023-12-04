"""Point-based reward system"""
from __future__ import annotations

import attrs
import numpy as np

from pooltool.ai.datatypes import State
from pooltool.ai.pot.core import required_precision, viable_pockets
from pooltool.events.datatypes import EventType
from pooltool.events.filter import filter_ball, filter_type
from pooltool.game.ruleset.utils import is_numbered_ball_pocketed


def is_legal_pot(state: State) -> bool:
    if not state.game.shot_info.legal:
        return False

    return is_numbered_ball_pocketed(state.system)


def is_legal_shot(state: State) -> bool:
    return state.game.shot_info.legal


def precision_of_next_pot(state: State) -> float:
    """The precision score between [0, 1] required for potting the next ball"""
    if state.game.shot_info.game_over:
        return 0.0

    return 0.5

    # FIXME

    next_ball = state.system.balls[state.game.shot_constraints.hittable[0]]
    cue = state.system.balls[state.system.cue.cue_ball_id]

    options = viable_pockets(
        cue, next_ball, state.system.table, state.system.balls.values()
    )

    from pooltool.ai.pot.core import viable_pockets

    viable_pockets(shot.balls["cue"], shot.balls["1"], shot.table, shot.balls.values())

    if not len(options):
        return 1.0


def precision_of_pot(state: State) -> float:
    """The precision score between [0, 1] required for the pot"""
    return 0.5


def difficulty_of_speed(state: State) -> float:
    """The difficulty required to apply this much speed"""
    V0 = state.system.cue.V0
    return 1 / (1 + np.exp(-2 * (V0 - 2.5)))


def difficulty_of_english(state: State) -> float:
    """The difficulty requird to apply this english state"""
    tau = 1 / 8
    side_spin = np.abs(state.system.cue.a)
    return 1 - np.exp(-(side_spin**2) / tau)


def complexity(state: State) -> float:
    """The complexity of the shot

    Hitting any circular cushion segments (where two linear segments meet) increases
    complexity drastically. Additionally, each ball the cue collids with after the first
    ball increases the complexity incrementally.
    """
    cue_events = filter_ball(
        state.system.events,
        "cue",
    )

    if len(filter_type(cue_events, EventType.BALL_CIRCULAR_CUSHION)) > 0:
        return 1.0

    # Cue ball collisions after first hit
    post_first_hit_collisions = len(filter_type(cue_events, EventType.BALL_BALL)) - 1

    return min(1, post_first_hit_collisions / 3)


@attrs.define
class RewardPointBased:
    """Reward based on point system"""

    def calc(self, state: State, debug: bool = False) -> float:
        if not is_legal_shot(state):
            return -0.1

        if not is_legal_pot(state):
            return 0.0

        weights = {
            precision_of_pot: 0.2,
            precision_of_next_pot: 0.2,
            difficulty_of_speed: 0.2,
            difficulty_of_english: 0.2,
            complexity: 0.2,
        }

        assert np.abs(sum(weights.values()) - 1) < 0.001

        reward = 0

        if debug:
            print("---")
            for func, weight in weights.items():
                reward += (1 - func(state)) * weight
                print(f"{func.__name__:.<45}: {func(state)}")
            print(f"{'Total reward':.<45}: {reward}")
        else:
            for func, weight in weights.items():
                reward += (1 - func(state)) * weight

        return reward
