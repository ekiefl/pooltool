from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from pooltool.potting.simple import calc_potting_angle, pick_best_pot


@dataclass
class PottingConfig:
    calculate_angle: Callable
    choose_pocket: Callable

    @staticmethod
    def default() -> PottingConfig:
        return PottingConfig(
            calculate_angle=calc_potting_angle,
            choose_pocket=pick_best_pot,
        )
