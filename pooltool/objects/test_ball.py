import numpy as np

from pooltool.constants import stationary
from pooltool.objects.ball.datatypes import BallState, _null_rvw


def test__null_rvw():
    # Assert unique array for multiple calls
    rvw = _null_rvw()
    rvw[0] = [1, 1, 1]
    rvw2 = _null_rvw()
    assert not np.array_equal(rvw, rvw2, equal_nan=True)


def test_ball_state_default():
    ball = BallState.default()

    assert ball.s == stationary
    assert ball.t == 0
    assert np.array_equal(ball.rvw, _null_rvw(), equal_nan=True)


def test_ball_state_copy():
    state = BallState.default()
    other = state.copy()

    # The states are equal
    assert state == other

    state.rvw[0] = [1, 1, 1]

    # After modifying original they are not
    assert state != other
