from __future__ import annotations

import attrs
import numpy as np

from pooltool.ai.datatypes import State
from pooltool.events.datatypes import EventType
from pooltool.events.filter import by_ball, by_type, filter_events
from pooltool.game.ruleset.utils import (
    StateProbe,
    get_lowest_ball,
    is_numbered_ball_pocketed,
)
from pooltool.ptmath import norm3d


def _is_legal_pot(state: State) -> bool:
    if not state.game.shot_info.legal:
        return False

    return is_numbered_ball_pocketed(state.system)


def _illegal_score(state: State) -> float:
    return 0.0 if state.game.shot_info.legal else 1.0


def _win_score(state: State) -> float:
    info = state.game.shot_info
    return 1.0 if (info.legal and info.game_over) else 0.0


def _distance_score(state: State) -> float:
    target = get_lowest_ball(state.system, when=StateProbe.START)
    cue = state.system.balls["cue"]
    dist = norm3d(target.history[0].rvw[0] - cue.history[0].rvw[0])
    table_length = state.system.table.l
    dist = min(dist, table_length)
    return (table_length - dist) / (table_length)


def _angle_between_vectors(v1, v2):
    """
    Calculates the smallest absolute angle in degrees between two 2D vectors.

    Args:
    v1, v2: Arrays or lists representing 2D vectors

    Returns:
    The smallest angle in degrees between the two vectors.
    """
    # Convert vectors to numpy arrays
    v1, v2 = np.array(v1), np.array(v2)

    # Calculate the dot product of the vectors
    dot_product = np.dot(v1, v2)

    # Calculate the magnitudes of the vectors
    magnitude_v1 = np.linalg.norm(v1)
    magnitude_v2 = np.linalg.norm(v2)

    # Calculate the cosine of the angle
    cos_angle = dot_product / (magnitude_v1 * magnitude_v2)

    # To handle numerical issues and ensure the value lies between -1 and 1
    cos_angle = np.clip(cos_angle, -1.0, 1.0)

    # Calculate the angle in radians and then convert it to degrees
    angle = np.arccos(cos_angle)
    angle_degrees = np.degrees(angle)

    return np.abs(angle_degrees)


def _cut_score(state: State) -> float:
    ball_ball_events = filter_events(
        state.system.events,
        by_type(EventType.BALL_BALL),
    )

    if not len(ball_ball_events):
        return 0.0

    agents = ball_ball_events[0].agents
    cue_agent = agents[0] if agents[0].id == "cue" else agents[1]
    other_agent = agents[1] if agents[0].id == "cue" else agents[0]

    v0 = cue_agent.initial.state.rvw[1][:2]  # type: ignore
    r01 = cue_agent.initial.state.rvw[0][:2]  # type: ignore
    r02 = other_agent.initial.state.rvw[0][:2]  # type: ignore

    angle = _angle_between_vectors(v0, r02 - r01)
    return (90 - angle) / 90


def _speed_score(state: State) -> float:
    V0 = state.system.cue.V0
    return 1 / (1 + np.exp(2 * (V0 - 1.5)))


def _english_score(state: State) -> float:
    """Punish side-spin"""
    tau = 1 / 8
    side_spin = np.abs(state.system.cue.a)
    return np.exp(-(side_spin**2) / tau)


def _cue_travel_score(state: State) -> float:
    dist = 0
    cue_history = state.system.balls["cue"].history

    curr_state = cue_history[0]
    for idx in range(1, len(cue_history)):
        next_state = cue_history[idx]
        dist += norm3d(next_state.rvw[0] - curr_state.rvw[0])
        curr_state = next_state

    M = state.system.table.l * 1.5
    dist = min(M, dist)
    return (M - dist) / M


def _simplicity(state: State) -> float:
    collisions = filter_events(
        state.system.events,
        by_ball("cue"),
        by_type(
            [
                EventType.BALL_BALL,
                EventType.BALL_LINEAR_CUSHION,
                EventType.BALL_CIRCULAR_CUSHION,
            ]
        ),
    )

    num_collisions = len(collisions)
    return max(0, (7 - num_collisions) / 6)


@attrs.define
class RewardMinimal:
    """Point-based reward system

    Very simple reward system that avoids baking in priors. There are two things that it
    rewards:

    (1) How complex is the shot? The metric used is the number of collisions. Less
        complex shots get higher reward.
    (2) How difficult is the shot to execute? This is measured by a weighted combination
        of how sharp the cut angle is, the amount of side spin applied, the distance
        between the cue and object ball, and the cue-stick impact speed. Less difficult
        shots get higher reward.
    """

    def ease(self, state: State) -> float:
        weights = {
            _cut_score: 0.3,
            _english_score: 0.3,
            _distance_score: 0.3,
            _speed_score: 0.1,
        }

        assert np.abs(sum(weights.values()) - 1) < 0.001
        return sum(func(state) * score for func, score in weights.items())

    def simplicity(self, state: State) -> float:
        return _simplicity(state)

    def calc(self, state: State, debug: bool = False) -> float:
        if score := _illegal_score(state) > 0:
            return score * -0.1

        if not _is_legal_pot(state):
            return 0.0

        weights = {
            self.ease: 0.3,
            self.simplicity: 0.7,
        }

        assert np.abs(sum(weights.values()) - 1) < 0.001

        reward = sum(func(state) * score for func, score in weights.items())

        if debug:
            print(reward)

        return reward
