import numpy as np
import pytest

import pooltool.constants as const
from pooltool.objects.ball.datatypes import Ball
from pooltool.physics.resolve.ball_off_table import (
    BallOffTableModel,
    FreezeOffTable,
    ball_off_table_models,
)


@pytest.fixture
def ball() -> Ball:
    ball = Ball.create("cue")
    ball.state.rvw[0] = [-0.05, 0.5, 0.1]
    ball.state.rvw[1] = [-2.0, 0.3, 1.0]
    ball.state.rvw[2] = [1.0, 2.0, 3.0]
    ball.state.s = const.airborne
    return ball


def test_freeze_keeps_position_and_removes_momentum(ball: Ball):
    position = ball.state.rvw[0].copy()

    resolved = FreezeOffTable().resolve(ball, inplace=True)

    assert resolved.state.s == const.off_table
    assert resolved.state.rvw[0] == pytest.approx(position)
    assert resolved.state.rvw[1] == pytest.approx(np.zeros(3))
    assert resolved.state.rvw[2] == pytest.approx(np.zeros(3))


def test_resolve_copies_unless_inplace(ball: Ball):
    resolved = FreezeOffTable().resolve(ball, inplace=False)

    assert resolved.state.s == const.off_table
    assert ball.state.s == const.airborne
    assert ball.state.rvw[1] == pytest.approx([-2.0, 0.3, 1.0])


def test_registry():
    assert ball_off_table_models[BallOffTableModel.FREEZE] is FreezeOffTable
