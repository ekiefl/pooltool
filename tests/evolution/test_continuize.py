import numpy as np
import pytest

from pooltool.evolution.continuize import continuize, interpolate_ball_states
from pooltool.evolution.event_based.simulate import simulate
from pooltool.system import System


def test_continuize_inplace():
    # Simulate a system
    system = simulate(System.example())

    # Now continuize it (no inplace)
    continuized_system = continuize(system, inplace=False)

    # Passed system is not continuized
    assert not system.continuized

    # Returned system is
    assert continuized_system.continuized

    # Simulate another system
    system = simulate(System.example())

    # Now continuize it (inplace)
    continuized_system = continuize(system, inplace=True)

    # Passed system is continuized
    assert system.continuized

    # Returned system is continuized
    assert continuized_system.continuized

    # They are the same object
    assert continuized_system is system


def test_interpolate_ball_states_exact_match():
    """Test interpolation at exact timestamps from history."""
    # Simulate and continuize a system
    system = simulate(System.example())
    ball = system.balls["cue"]

    # Pick specific timestamps from history
    t0 = ball.history[3].t
    t1 = ball.history[4].t
    timestamps = np.array([t0, t1])

    # Interpolate at those exact timestamps
    states = interpolate_ball_states(ball, timestamps)

    # Should match exactly
    assert len(states) == 2
    assert states[0] == ball.history[3]
    assert states[1] == ball.history[4]


def test_interpolate_ball_states_intermediate():
    """Test interpolation at timestamps between history entries."""
    system = simulate(System.example())
    ball = system.balls["cue"]

    # Pick a timestamp between two history entries
    t0 = ball.history[0].t
    t1 = ball.history[1].t
    t_mid = (t0 + t1) / 2

    # Interpolate at the midpoint
    states = interpolate_ball_states(ball, [t_mid])

    # Should be a valid state
    assert states[0].t == t_mid


def test_interpolate_ball_states_out_of_range():
    """Test behavior when timestamps are outside the history range."""
    # Simulate a system
    system = simulate(System.example())
    ball = system.balls["cue"]

    # Timestamp before history starts
    t_before = ball.history[0].t - 1.0

    # Timestamp after history ends
    t_after = ball.history[-1].t + 1.0

    # Raises error when extrapolate is False
    with pytest.raises(ValueError):
        interpolate_ball_states(ball, [t_before])

    with pytest.raises(ValueError):
        interpolate_ball_states(ball, [t_after])

    # Returns boundary states when extrapolate is True
    before_states = interpolate_ball_states(ball, [t_before], extrapolate=True)
    assert len(before_states) == 1
    assert before_states[0] == ball.history[0]

    after_states = interpolate_ball_states(ball, [t_after], extrapolate=True)
    assert len(after_states) == 1
    assert after_states[0] == ball.history[-1]


def test_interpolate_ball_states_empty_history():
    """Test behavior with empty history."""
    # Create a ball with empty history
    system = System.example()
    ball = system.balls["cue"]

    # Should raise error
    with pytest.raises(ValueError, match="Cannot interpolate from empty history"):
        interpolate_ball_states(ball, [0.5])
