from __future__ import annotations

from typing import Callable, Optional

from attrs import define

from pooltool.ai.pot.core import calc_potting_angle, pick_easiest_pot
from pooltool.objects import Ball, Pocket, Table
from pooltool.system.datatypes import System


@define
class PottingConfig:
    calculate_angle: Callable[[Ball, Ball, Table, Pocket], float]
    choose_pocket: Callable[[System, Ball], Optional[Pocket]]

    @staticmethod
    def default() -> PottingConfig:
        return PottingConfig(
            calculate_angle=calc_potting_angle,
            choose_pocket=pick_easiest_pot,
        )
