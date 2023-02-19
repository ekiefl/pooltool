from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from pooltool.constants import stationary
from pooltool.objects.ball.datatypes import (
    BallHistory,
    BallParams,
    BallState,
    _null_rvw,
)


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

    # The states are equal but they are different objects
    assert state is not other
    assert state == other

    state.rvw[0] = [1, 1, 1]

    # After modifying original they are no longer equal
    assert state != other


def test_ball_history_empty():
    empty_history = BallHistory()
    assert not len(empty_history)
    assert empty_history.empty


def test_ball_history_equality():
    """Test whether ball histories are equal

    This is an important test, because BallHistory contains BallState, which uses a
    special __eq__ method that handles numpy arrays.
    """
    state1 = BallState.default()
    state1.rvw[0] = [1, 1, 1]

    state2 = BallState.default()
    state2.rvw[0] = [2, 2, 2]

    history1 = BallHistory(states=[state1])
    history2 = BallHistory(states=[state2])

    assert history1 == history1
    assert history2 == history2
    assert history1 != history2


def test_ball_history_add():
    # Init history
    history = BallHistory()
    assert history.empty

    # Make state with t = 1
    state = BallState.default()
    state.t = 1

    # Add state to history
    history.add(state)
    assert not history.empty

    # `add` makes a copy of the state, so verify they are two different objects
    assert history[0] is not state

    # But they do equate
    assert history[0] == state

    # Until one of them is modified
    state.t = 0
    assert history[0] != state

    # You can't add a state with a time less than the last entry
    with pytest.raises(AssertionError):
        history.add(state)

    # Making time of state greater than the last entry works
    state.t = 2
    history.add(state)
    assert len(history) == 2


def test_ball_params():
    params = BallParams()

    # Params are frozen
    with pytest.raises(FrozenInstanceError):
        params.u_r = 4

    # Partial specification OK
    other = BallParams(m=0.24)
    assert params.m != other.m
    assert params.R == other.R
    assert params.u_r == other.u_r
    assert params.u_sp == other.u_sp
