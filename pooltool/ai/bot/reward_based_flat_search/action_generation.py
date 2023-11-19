from typing import Callable, Dict, List, Optional

import attrs

from pooltool.ai.action import Action
from pooltool.ai.datatypes import State
from pooltool.ai.potting import PottingConfig
from pooltool.ai.potting.simple import calc_potting_angle, pick_best_pot
from pooltool.ai.reward.nine_ball import RewardPointBased
from pooltool.ai.utils import between, random_params
from pooltool.evolution.event_based.simulate import simulate
from pooltool.game.datatypes import GameType
from pooltool.game.ruleset import get_ruleset
from pooltool.game.ruleset.datatypes import Ruleset
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.table.components import Pocket
from pooltool.system.datatypes import System

AIMER = PottingConfig(
    calculate_angle=calc_potting_angle,
    choose_pocket=pick_best_pot,
)


def random_action() -> Action:
    return random_params(
        V0=(0.5, 4),
        phi=(0, 360),
        theta=(0.0, 0.0),
        a=(-0.5, 0.5),
        b=(-0.2, 0.2),
    )


def get_best_aiming_phi(system: System, game: Ruleset) -> float:
    cue_ball = system.balls[system.cue.cue_ball_id]
    target_ball = system.balls[game.shot_constraints.hittable[0]]
    pockets = list(system.table.pockets.values())

    return AIMER.calculate_angle(
        cue_ball,
        target_ball,
        AIMER.choose_pocket(cue_ball, target_ball, pockets),
    )


def apply_phi_to_action(phi: float, dphi: float, action: Action) -> Action:
    action.phi = between(phi - dphi, phi + dphi)
    return action


def get_break_action(system: System, game: Ruleset) -> Action:
    target_ball = system.balls[game.shot_constraints.hittable[0]]

    # Bad API, we only have a method that modifies in place, so we take a copy,
    # modify in place, record the new state, and set system back to old state
    initial_action = Action.from_cue(system.cue)
    system.aim_at_ball(target_ball.id, cut=between(-5, 5))
    action = Action.from_cue(system.cue)
    assert initial_action != action, f"Modify in place gone wrong"
    initial_action.apply(system.cue)

    action.V0 = 7.0
    action.theta = 0.0
    action.a = 0.0
    action.b = 0.2

    return action
