"""Tests for the frictional, inelastic ball-table collision (landing).

Both landing impulses (normal and friction) act at the contact point, -R z. Their
moment about the vertical axis is therefore zero, so a landing must never change w_z,
whether the ball sticks (no-slip branch) or slips (slip branch).
"""

import numpy as np
import pytest
from numpy.typing import NDArray

import pooltool as pt
from pooltool.physics.resolve.ball_table import FrictionalInelasticTable

PARAMS = pt.BallParams.default(pt.GameType.THREECUSHION)
R = PARAMS.R
UNIT_Z = np.array([0.0, 0.0, 1.0])


def land(v: NDArray[np.float64], w: NDArray[np.float64]) -> NDArray[np.float64]:
    """Land a ball with velocity v and angular velocity w; return the new rvw."""
    ball = pt.Ball(id="cue", params=PARAMS)
    ball.state = pt.objects.BallState(
        np.array([[0.7, 1.4, R], v, w], dtype=float), pt.constants.airborne
    )
    return FrictionalInelasticTable().resolve(ball).state.rvw


@pytest.mark.parametrize("roll_fraction", [1.0, 0.98, 0.9, 0.7, 0.0])
@pytest.mark.parametrize("w_z", [-20.0, 0.0, 35.0])
def test_landing_keeps_w_z_and_matches_angular_impulse(
    roll_fraction: float, w_z: float
):
    """Covers both branches: roll_fraction 1 sticks, roll_fraction 0 slips.

    The spin change must equal the angular impulse of the model's own linear impulse
    at the contact point: dw = (5 / 2R) * (dv x z).
    """
    v = np.array([0.3, 1.5, -0.15])
    w = np.array([-roll_fraction * v[1] / R, roll_fraction * v[0] / R, w_z])

    rvw = land(v, w)

    assert rvw[2, 2] == pytest.approx(w_z, abs=1e-12)
    dv = rvw[1] - v
    np.testing.assert_allclose(rvw[2] - w, 2.5 / R * np.cross(dv, UNIT_Z), atol=1e-9)


@pytest.mark.parametrize("w_z", [-20.0, 35.0])
def test_landing_continuous_at_branch_switch(w_z: float):
    """The outcome is continuous where the no-slip and slip branches meet."""
    v = np.array([0.0, 1.5, -0.15])
    # Natural roll about x, plus a lateral contact slip R*|w_y| right at the Coulomb
    # limit: (2/7)|u| = u_s (1 + e_t) |v_z|.
    limit = 3.5 * PARAMS.u_s * (1 + PARAMS.e_t) * -v[2]

    below = land(v, np.array([-v[1] / R, limit * (1 - 1e-7) / R, w_z]))
    above = land(v, np.array([-v[1] / R, limit * (1 + 1e-7) / R, w_z]))

    np.testing.assert_allclose(below[1:], above[1:], rtol=1e-5, atol=1e-6)
