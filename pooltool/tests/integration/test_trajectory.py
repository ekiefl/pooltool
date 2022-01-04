#! /usr/bin/env python

from pooltool.tests import ref, trial

import numpy as np

def test_trajectories(ref, trial):
    for ball_ref in ref.balls.values():
        ball_trial = trial.balls[ball_ref.id]

        np.testing.assert_allclose(ball_ref.rvw, ball_trial.rvw)
        np.testing.assert_allclose(ball_ref.s, ball_trial.s)
        np.testing.assert_allclose(ball_ref.t, ball_trial.t)
        np.testing.assert_allclose(ball_ref.history.rvw, ball_trial.history.rvw)
        np.testing.assert_allclose(ball_ref.history.s, ball_trial.history.s)
        np.testing.assert_allclose(ball_ref.history.t, ball_trial.history.t)
        np.testing.assert_allclose(ball_ref.history_cts.rvw, ball_trial.history_cts.rvw)
        np.testing.assert_allclose(ball_ref.history_cts.s, ball_trial.history_cts.s)
        np.testing.assert_allclose(ball_ref.history_cts.t, ball_trial.history_cts.t)
