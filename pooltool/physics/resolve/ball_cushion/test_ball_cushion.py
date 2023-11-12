import numpy as np
import pytest

from pooltool.constants import sliding
from pooltool.objects import Ball, BallParams, LinearCushionSegment, PocketTableSpecs
from pooltool.physics.resolve.ball_cushion import (
    BallLCushionModel,
    get_ball_lin_cushion_model,
)


@pytest.fixture
def cushion_yaxis():
    """A cushion with edge along the y-axis"""
    h = PocketTableSpecs().cushion_height

    return LinearCushionSegment(
        "cushion",
        p1=np.array([0, -1, h], dtype=np.float64),
        p2=np.array([0, +1, h], dtype=np.float64),
    )


@pytest.mark.parametrize(
    "model_name", [BallLCushionModel.HAN_2005, BallLCushionModel.UNREALISTIC]
)
def test_symmetry(
    cushion_yaxis: LinearCushionSegment, model_name: BallLCushionModel
) -> None:
    """Test that ball-linear cushion interactions are symmetric"""
    R = BallParams.default().R
    pos = [-R, 0, R]

    for theta in np.linspace(-89, 89, 20):
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
        model = get_ball_lin_cushion_model(model_name)
        ball_after, _ = model.resolve(ball=ball, cushion=cushion_yaxis, inplace=False)
        other_after, _ = model.resolve(ball=other, cushion=cushion_yaxis, inplace=False)

        # The velocities have been updated
        assert not np.array_equal(ball.state.rvw[1], ball_after.state.rvw[1])
        assert not np.array_equal(other.state.rvw[1], other_after.state.rvw[1])

        # X-velocties are negative and the same
        assert ball_after.state.rvw[1, 0] < 0
        assert other_after.state.rvw[1, 0] < 0
        assert np.isclose(ball_after.state.rvw[1, 0], other_after.state.rvw[1, 0])

        # Y-velocities are reflected
        assert ball_after.state.rvw[1, 1] == -other_after.state.rvw[1, 1]
