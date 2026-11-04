import numpy as np
import pytest

from pooltool.objects import (
    CircularCushionSegment,
    LinearCushionSegment,
    PocketTableSpecs,
)


@pytest.fixture
def cushion() -> LinearCushionSegment:
    specs = PocketTableSpecs()

    return LinearCushionSegment(
        "cushion",
        p1=np.array([0, -1, specs.cushion_height], dtype=np.float64),
        p2=np.array([0, +1, specs.cushion_height], dtype=np.float64),
        nose_radius=specs.cushion_nose_radius,
    )


@pytest.fixture
def cushion_circular() -> CircularCushionSegment:
    specs = PocketTableSpecs()

    return CircularCushionSegment(
        "pocket_cushion",
        center=np.array([0.0, 0.0, specs.cushion_height], dtype=np.float64),
        radius=0.01,
        nose_radius=specs.cushion_nose_radius,
    )
