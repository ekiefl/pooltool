import numpy as np
import pytest

from pooltool import physics
from pooltool.constants import sliding
from pooltool.objects import Ball, BallParams, LinearCushionSegment
from pooltool.physics.resolve.ball_cushion import (
    BallLCushionModel,
    ball_lcushion_models,
)


@pytest.mark.parametrize(
    "model_name",
    [
        BallLCushionModel.UNREALISTIC,
        BallLCushionModel.HAN_2005,
        BallLCushionModel.IMPULSE_FRICTIONAL_INELASTIC_2D,
        BallLCushionModel.MATHAVAN_2010,
        BallLCushionModel.STRONGE_COMPLIANT,
    ],
)
@pytest.mark.parametrize("theta", np.linspace(1, 89, 10))
def test_energy(
    cushion: LinearCushionSegment, model_name: BallLCushionModel, theta: float
) -> None:
    """Test that ball-linear cushion interactions do not increase energy"""
    R = BallParams.default().R
    pos = [-R, 0, R]

    rads = np.radians(theta)
    vel = [np.cos(rads), np.sin(rads), 0]

    # Ball hitting left-side of cushion
    ball = Ball("cue")
    ball.state.rvw[0] = pos
    ball.state.rvw[1] = vel
    ball.state.s = sliding

    initial_energy = physics.get_ball_energy(
        ball.state.rvw,
        ball.params.R,
        ball.params.m,
        ball.params.g,
    )

    # Resolve physics
    model = ball_lcushion_models[model_name]()
    ball_after, _ = model.resolve(ball=ball, cushion=cushion, inplace=False)

    final_energy = physics.get_ball_energy(
        ball_after.state.rvw,
        ball_after.params.R,
        ball_after.params.m,
        ball_after.params.g,
    )

    assert np.isclose(initial_energy, final_energy) or final_energy <= initial_energy, (
        "energy must not increase during collisions"
    )


@pytest.mark.parametrize(
    "model_name",
    [
        BallLCushionModel.UNREALISTIC,
        BallLCushionModel.HAN_2005,
        BallLCushionModel.IMPULSE_FRICTIONAL_INELASTIC_2D,
        BallLCushionModel.MATHAVAN_2010,
        BallLCushionModel.STRONGE_COMPLIANT,
    ],
)
@pytest.mark.parametrize("theta", np.linspace(-89, 89, 20))
def test_symmetry(
    cushion: LinearCushionSegment, model_name: BallLCushionModel, theta: float
) -> None:
    """Test that ball-linear cushion interactions are symmetric"""
    R = BallParams.default().R
    pos = [-R, 0, R]

    rads = np.radians(theta)
    vel = [np.cos(rads), np.sin(rads), 0]

    # Ball hitting left-side of cushion
    ball = Ball("cue")
    ball.state.rvw[0] = pos
    ball.state.rvw[1] = vel
    ball.state.s = sliding

    # Ball hitting left-side of cushion with opposite y-vel
    other = ball.copy()
    other.state.rvw[1, 1] = -ball.state.rvw[1, 1]

    # Positions are same
    assert np.array_equal(ball.state.rvw[0], other.state.rvw[0])

    # X-velocities are the same
    assert ball.state.rvw[1, 0] == other.state.rvw[1, 0]

    # Y-velocities are the reflected
    assert ball.state.rvw[1, 1] == -other.state.rvw[1, 1]

    # Resolve physics
    model = ball_lcushion_models[model_name]()
    ball_after, _ = model.resolve(ball=ball, cushion=cushion, inplace=False)
    other_after, _ = model.resolve(ball=other, cushion=cushion, inplace=False)

    # The velocities have been updated
    assert not np.array_equal(ball.state.rvw[1], ball_after.state.rvw[1])
    assert not np.array_equal(other.state.rvw[1], other_after.state.rvw[1])

    # X-velocties are negative and the same
    assert ball_after.state.rvw[1, 0] < 0
    assert other_after.state.rvw[1, 0] < 0
    assert np.isclose(ball_after.state.rvw[1, 0], other_after.state.rvw[1, 0])

    # Y-velocities are reflected
    assert np.isclose(ball_after.state.rvw[1, 1], -other_after.state.rvw[1, 1])
