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


@pytest.fixture
def cushion_ring() -> CircularCushionSegment:
    """A nose circle wide enough that a ball on the table fits inside it.

    The horizontal reach of the nose tube at table height is about 28 mm for a pool
    ball, so a 50 mm nose circle leaves an inner contact circle on the table as well
    as the usual outer one.
    """
    specs = PocketTableSpecs()

    return CircularCushionSegment(
        "ring_cushion",
        center=np.array([0.0, 0.0, specs.cushion_height], dtype=np.float64),
        radius=0.05,
        nose_radius=specs.cushion_nose_radius,
    )
