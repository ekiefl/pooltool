from typing import Tuple

import numpy as np

from pooltool.ai.datatypes import Action


def between(low: float, high: float) -> float:
    return (high - low) * np.random.rand() + low


def random_params(
    V0: Tuple[float, float] = (0.5, 4),
    phi: Tuple[float, float] = (0, 360),
    theta: Tuple[float, float] = (0, 0),
    a: Tuple[float, float] = (-0.5, 0.5),
    b: Tuple[float, float] = (-0.5, 0.5),
) -> Action:
    return Action(
        V0=between(*V0),
        phi=between(*phi),
        theta=between(*theta),
        a=between(*a),
        b=between(*b),
    )
