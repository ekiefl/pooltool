from __future__ import annotations

from typing import Callable, Optional, Sequence

from attrs import define

from pooltool.ai.pot.core import calc_potting_angle, pick_easiest_pot
from pooltool.objects import Ball, Pocket, Table
from pooltool.system.datatypes import System


@define
class PottingConfig:
    calculate_angle: Callable[[Ball, Ball, Table, Pocket], float]
    choose_pocket: Callable[[Ball, Ball, Table, Optional[Sequence[Pocket]]], Pocket]

    @staticmethod
    def default() -> PottingConfig:
        return PottingConfig(
            calculate_angle=calc_potting_angle,
            choose_pocket=pick_easiest_pot,
        )


def aim_for_pocket(
    system: System,
    ball_id: str,
    pocket_id: str,
    config: PottingConfig = PottingConfig.default(),
):
    """Set phi to pot a given ball into a given pocket"""
    assert system.cue.cue_ball_id in system.balls

    system.cue.set_state(
        phi=config.calculate_angle(
            system.balls[system.cue.cue_ball_id],
            system.balls[ball_id],
            system.table,
            system.table.pockets[pocket_id],
        )
    )


def aim_for_best_pocket(
    system: System, ball_id: str, config: PottingConfig = PottingConfig.default()
):
    """Set phi to pot a given ball into the best/easiest pocket"""
    assert system.cue.cue_ball_id in system.balls

    cue_ball = system.balls[system.cue.cue_ball_id]
    object_ball = system.balls[ball_id]
    table = system.table
    pockets = list(system.table.pockets.values())

    aim_for_pocket(
        system=system,
        ball_id=ball_id,
        pocket_id=config.choose_pocket(cue_ball, object_ball, table, pockets).id,
        config=config,
    )
