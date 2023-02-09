from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from pooltool.potting.simple import calc_potting_angle as calc_potting_angle_simple


@dataclass
class PottingConfig:
    method: Callable

    @staticmethod
    def default() -> PottingConfig:
        return PottingConfig(
            method=calc_potting_angle_simple,
        )
