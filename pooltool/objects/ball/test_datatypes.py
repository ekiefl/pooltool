import numpy as np
import pytest
from attrs.exceptions import FrozenInstanceError

from pooltool.constants import stationary
from pooltool.objects.ball.datatypes import (
    Ball,
    BallHistory,
    BallOrientation,
    BallParams,
    BallState,
    _null_rvw,
)
from pooltool.objects.ball.sets import get_ballset


def test__null_rvw():
    # Assert unique array for multiple calls
    rvw = _null_rvw()
    rvw[0] = [1, 1, 1]
    rvw2 = _null_rvw()
    assert not np.array_equal(rvw, rvw2, equal_nan=True)


def test_ball_orientation():
    orientation = BallOrientation.random()

    # Frozen
    with pytest.raises(FrozenInstanceError):
        orientation.pos = (1.0, 1.0, 1.0, 1.0)  # type: ignore


# ------ BallState


def test_ball_state_default():
    ball = BallState.default()

    assert ball.s == stationary
    assert ball.t == 0
    assert np.array_equal(ball.rvw, _null_rvw(), equal_nan=True)


def test_ball_state_copy():
    state = BallState.default()
    other = state.copy()

    # The states are equal but they are different objects
    assert state.rvw is not other.rvw
    assert state is not other
    assert state == other

    state.rvw[0] = [1, 1, 1]

    # After modifying original they are no longer equal
    assert state != other


# ------ BallHistory


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


def test_ball_history_vectorize():
    history = BallHistory()

    # Empty history returns None
    assert history.vectorize() is None

    # Append same state 10 times
    state = BallState.default()
    state.rvw[0] = [1, 1, 1]
    for _ in range(10):
        history.add(state)

    assert (vectorize := history.vectorize()) is not None
    rvws, motion_states, t = vectorize

    assert np.array_equal(rvws, np.array([state.rvw] * 10))
    assert np.array_equal(motion_states, np.array([0] * 10))
    assert np.array_equal(t, np.array([0] * 10))

    # Round trip
    assert BallHistory.from_vectorization(history.vectorize()) == history


def test_ball_history_copy():
    # Create a history of 10 states
    history = BallHistory()
    state = BallState.default()
    state.rvw[0] = [1, 1, 1]
    for _ in range(10):
        history.add(state)

    # Create a copy of history
    copy = history.copy()

    # Copy equals original
    assert copy == history

    # Modifying original does not modify copy
    history.states[0].t = 100
    history.states[0].rvw[0] = [0, 0, 0]
    assert copy != history


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

    # `add` appends the state directly, just list how lists append. So verify they are
    # the same objects
    assert history[0] is state

    # Therefore modifying the state modifies the history
    state.t = 2
    assert history[0] == state

    # You can't add a state with a time less than the last entry
    with pytest.raises(AssertionError):
        new_state = state.copy()
        new_state.t = 1
        history.add(new_state)

    # Making time of state greater than the last entry works
    state.t = 2
    history.add(state)
    assert len(history) == 2


# ------ BallParams


def test_ball_params():
    params = BallParams()

    # Params are frozen
    with pytest.raises(FrozenInstanceError):
        params.u_r = 4  # type: ignore

    # Partial specification OK
    other = BallParams(m=0.24)
    assert params.m != other.m
    assert params.R == other.R
    assert params.u_r == other.u_r
    assert params.u_sp == other.u_sp


# ------ Ball


def test_ballset():
    # Valid ballset
    ballset1 = get_ballset("pooltool_pocket")
    assert "cue" in ballset1.ids

    ball = Ball.create("cue", m=24, g=10.8, xy=[4, 2])
    assert ball.ballset is None
    ball.set_ballset(ballset1)
    assert ball.ballset == ballset1

    ball = Ball.create("cue", ballset=ballset1, m=24, g=10.8, xy=[4, 2])
    assert ball.ballset == ballset1


def test_ball_copy():
    ball = Ball.create("cue", m=24, g=10.8, xy=[4, 2])
    copy = ball.copy()

    # Ball and copy equate
    assert ball == copy

    # Various changes to ball do not affect copy...

    # Can't change `params` attributes period
    with pytest.raises(FrozenInstanceError):
        ball.params.m = 42  # type: ignore

    # Nor `initial_orientation` attributes
    with pytest.raises(FrozenInstanceError):
        ball.initial_orientation.pos = (1.0, 1.0, 1.0, 1.0)  # type: ignore

    # Assigning new params does not modify copy
    assert ball.params == copy.params
    ball.params = BallParams(m=42)
    assert ball.params != copy.params

    # Assigning new orientation does not modify copy
    assert ball.initial_orientation == copy.initial_orientation
    ball.initial_orientation = BallOrientation.random()
    assert ball.initial_orientation != copy.initial_orientation

    # Modifying state does not modify copy
    assert ball.state == copy.state
    ball.state.rvw[0] = [1, 1, 1]
    assert ball.state != copy.state
