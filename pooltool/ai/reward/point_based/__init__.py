"""Point-based reward system

To note: According to the current MCTS procedure, game.process_shot(...) and
game.advance(...) are called before these functions are called. This means
game.shot_info is up-to-date, yet the turn number, active player, etc. are not. If you
need the pre-advance game state, game.advance(...) should be called before expand and
after awarding points.
"""
from __future__ import annotations

from typing import Protocol

import attrs
import numpy as np

from pooltool.ai.datatypes import State
from pooltool.ai.potting.simple import (
    calc_cut_angle,
    calc_shadow_ball_center,
    pick_best_pot,
)
from pooltool.events.datatypes import EventType
from pooltool.events.filter import by_ball, by_type, filter_events
from pooltool.game.ruleset.utils import (
    StateProbe,
    get_lowest_ball,
    is_numbered_ball_pocketed,
)
from pooltool.ptmath import norm3d


class RewardFunction(Protocol):
    def __call__(self, state: State) -> float:
        ...


def is_legal_pot(state: State) -> bool:
    if not state.game.shot_info.legal:
        return False

    return is_numbered_ball_pocketed(state.system)


def illegal_score(state: State) -> float:
    return 0.0 if state.game.shot_info.legal else 1.0


def win_score(state: State) -> float:
    info = state.game.shot_info
    return 1.0 if (info.legal and info.game_over) else 0.0


def pot_score(state: State) -> float:
    return 1.0 if is_legal_pot(state) else 0.0


def distance_score(state: State) -> float:
    if state.game.shot_info.game_over:
        return 1.0

    next_target = get_lowest_ball(state.system, when=StateProbe.END)
    cue = state.system.balls["cue"]

    dist_vec = next_target.state.rvw[0] - cue.state.rvw[0]
    dist = norm3d(dist_vec)

    table_length = state.system.table.l

    dist = min(dist, table_length)
    return (table_length - dist) / (table_length)


def _cut_score(
    angle: float,
    optimal_start: float = 7.5,
    optimal_end: float = 20.0,
    decay_end: float = 70.0,
):
    if angle < optimal_start:
        # Linear interpolation between 0.3 at angle 0 and 1 at angle optimal_angle
        return 0.3 + (1 - 0.3) * (angle / optimal_start)
    elif angle < optimal_end:
        # Maintain score of 1 between optimal_angle and decay_start
        return 1
    else:
        # Exponential decay from decay_start to decay_end
        decay_rate = -np.log(0.01) / (
            decay_end - optimal_end
        )  # rate to reach close to 0 at decay_end
        return np.exp(-decay_rate * (angle - optimal_end))


def cut_score(state: State) -> float:
    if state.game.shot_info.game_over:
        return 1.0

    cue = state.system.balls["cue"]
    next_target = get_lowest_ball(state.system, when=StateProbe.END)
    pocket = pick_best_pot(cue, next_target, list(state.system.table.pockets.values()))

    cut_angle = calc_cut_angle(
        c=cue.xyz[:2],
        b=calc_shadow_ball_center(next_target, pocket),
        p=pocket.potting_point,
    )

    return _cut_score(np.abs(cut_angle))


def cue_collision_complexity_score(state: State) -> float:
    cue_ball_collisions = filter_events(
        state.system.events,
        by_ball("cue"),
        by_type(EventType.BALL_BALL),
    )

    num_collisions = len(cue_ball_collisions)

    if num_collisions == 1:
        return 1.0
    elif num_collisions == 2:
        return 0.3

    return 0.0


def object_collision_complexity_score(state: State) -> float:
    if not state.game.shot_info.legal:
        return 0.0

    object_ball_collisions = filter_events(
        state.system.events,
        by_ball(get_lowest_ball(state.system, when=StateProbe.START).id),
        by_type([EventType.BALL_BALL, EventType.BALL_LINEAR_CUSHION]),
    )

    num_collisions = len(object_ball_collisions)

    # Guaranteed 1 ball collision, and a cushion collision is also likely
    if num_collisions == 1:
        return 1.0
    elif num_collisions == 2:
        return 0.7
    elif num_collisions == 3:
        return 0.2

    return 0.0


def speed_score(state: State) -> float:
    V0 = state.system.cue.V0
    return 1 / (1 + np.exp(2 * (V0 - 1.5)))


def english_score(state: State) -> float:
    """Punish side-spin"""
    tau = 1 / 8
    side_spin = np.abs(state.system.cue.a)
    return np.exp(-(side_spin**2) / tau)


@attrs.define
class RewardPointBased:
    """Reward based on point system"""

    def calc(self, state: State, debug: bool = False) -> float:
        if score := illegal_score(state) > 0:
            return score * -0.1

        if not is_legal_pot(state):
            return 0.0

        weights = {
            cut_score: 0.30,
            speed_score: 0.25,
            distance_score: 0.20,
            cue_collision_complexity_score: 0.075,
            object_collision_complexity_score: 0.075,
            english_score: 0.10,
        }

        assert np.abs(sum(weights.values()) - 1) < 0.001

        reward = 0

        if debug:
            print("---")
            for func, weight in weights.items():
                reward += func(state) * weight
                print(f"{func.__name__:.<45}: {func(state) * weight}")
            print(f"{'Total':.<45}: {reward}")
        else:
            for func, weight in weights.items():
                reward += func(state) * weight

        return reward
