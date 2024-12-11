from math import isclose

import numpy as np
import pytest

from pooltool import constants
from pooltool.objects.ball.datatypes import Ball
from pooltool.physics.resolve.ball_table.core import (
    BallTableCollisionStrategy,
    bounce_height,
)
from pooltool.physics.resolve.ball_table.frictional_inelastic import FrictionalInelastic
from pooltool.physics.resolve.ball_table.frictionless_inelastic import (
    FrictionlessInelastic,
)


@pytest.mark.parametrize(
    "vz,g,expected",
    [
        (4.0, 9.8, 0.5 * 16 / 9.8),  # Typical scenario
        (0.0, 9.8, 0.0),  # No velocity, no bounce height
        (10.0, 9.8, 0.5 * 100 / 9.8),
        (2.5, 10.0, 0.5 * 6.25 / 10.0),
    ],
)
def test_bounce_height(vz, g, expected):
    result = bounce_height(vz, g)
    assert isclose(result, expected, rel_tol=1e-7), f"Expected {expected}, got {result}"


def test_bounce_height_negative_vz():
    # The function doesn't specify behavior for negative vz, but it still returns
    # a mathematically valid height based on vz^2. Let's just check correctness.
    vz = -3.0
    g = 9.8
    expected = 0.5 * (vz**2) / g
    result = bounce_height(vz, g)
    assert isclose(result, expected, rel_tol=1e-7), f"Expected {expected}, got {result}"


models = [FrictionlessInelastic(), FrictionalInelastic()]


def example() -> Ball:
    return Ball.create("cue", xy=(0, 0))


@pytest.mark.parametrize("model", models)
@pytest.mark.parametrize("vz0", -np.logspace(-5, 4, 10, base=10))
def test_non_negative_output_velocity(model: BallTableCollisionStrategy, vz0: float):
    ball = example()
    ball.state.rvw[1, 2] = vz0

    model.resolve(ball, inplace=True)

    # Final velocity should never be negative
    assert ball.state.rvw[1, 2] >= 0


@pytest.mark.parametrize("model", models)
@pytest.mark.parametrize("vz0", -np.logspace(-5, 4, 10, base=10))
def test_decaying_velocity(model: BallTableCollisionStrategy, vz0: float):
    ball = example()
    ball.state.rvw[1, 2] = vz0

    model.resolve(ball, inplace=True)

    # Final speed should never be greater than incoming speed
    assert ball.state.rvw[1, 2] <= -vz0


@pytest.mark.parametrize("model", models)
def test_positive_incoming_velocity_fails(model: BallTableCollisionStrategy):
    ball = example()
    ball.state.rvw[1, 2] = +1

    with pytest.raises(ValueError):
        model.resolve(ball, inplace=True)


@pytest.mark.parametrize("model", models)
def test_zero_incoming_velocity_fails(model: BallTableCollisionStrategy):
    ball = example()
    ball.state.rvw[1, 2] = 0.0

    with pytest.raises(ValueError):
        model.resolve(ball, inplace=True)


@pytest.mark.parametrize("model", models)
def test_non_airborne_outgoing_state(model: BallTableCollisionStrategy):
    """Test that a very small incoming velocity leads to non-airborne outgoing state.

    This is important to avoid perpetual bouncing"""
    ball = example()

    # A very small incoming velocity
    ball.state.rvw[1, 2] = -0.001

    model.resolve(ball, inplace=True)

    # Final state should not be airborne
    assert ball.state.s != constants.airborne
    assert ball.state.rvw[1, 2] == 0.0
