from typing import Tuple

import numpy as np
import pytest

from pooltool import constants
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.table.datatypes import Table
from pooltool.physics.resolve.ball_table.core import BallTableCollisionStrategy
from pooltool.physics.resolve.ball_table.frictionless_inelastic import (
    FrictionlessInelastic,
)

models = [
    FrictionlessInelastic(),
]


def example() -> Tuple[Ball, Table]:
    return Ball.create("cue", xy=(0, 0)), Table.default()


@pytest.mark.parametrize("model", models)
@pytest.mark.parametrize("vz0", -np.logspace(-5, 4, 10, base=10))
def test_non_negative_output_velocity(model: BallTableCollisionStrategy, vz0: float):
    ball, table = example()
    ball.state.rvw[1, 2] = vz0

    model.resolve(ball, table, inplace=True)

    # Final velocity should never be negative
    assert ball.state.rvw[1, 2] >= 0


@pytest.mark.parametrize("model", models)
@pytest.mark.parametrize("vz0", -np.logspace(-5, 4, 10, base=10))
def test_decaying_velocity(model: BallTableCollisionStrategy, vz0: float):
    ball, table = example()
    ball.state.rvw[1, 2] = vz0

    model.resolve(ball, table, inplace=True)

    # Final speed should never be greater than incoming speed
    assert ball.state.rvw[1, 2] <= -vz0


@pytest.mark.parametrize("model", models)
def test_non_negative_incoming_velocity_fails(model: BallTableCollisionStrategy):
    ball, table = example()
    ball.state.rvw[1, 2] = +1

    with pytest.raises(ValueError):
        model.resolve(ball, table, inplace=True)

    # Final velocity should never be negative
    assert ball.state.rvw[1, 2] >= 0


@pytest.mark.parametrize("model", models)
def test_non_airborne_outgoing_state(model: BallTableCollisionStrategy):
    """Test that a very small incoming velocity leads to non-airborne outgoing state.

    This is important to avoid perpetual bouncing"""
    ball, table = example()

    # A very small incoming velocity
    ball.state.rvw[1, 2] = -0.001

    model.resolve(ball, table, inplace=True)

    # Final state should not be airborne
    assert ball.state.s != constants.airborne
