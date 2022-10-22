#! /usr/bin/env python

import tempfile

import numpy as np
import pytest

import pooltool as pt
from pooltool.error import ConfigError
from pooltool.objects.ball import Ball
from pooltool.tests import ref, trial


def test_bad_id():
    with pytest.raises(ConfigError):
        Ball(234.2)


def test_save(trial):
    for ball in trial.balls.values():
        filepath = pt.utils.get_temp_file_path()
        ball.save(filepath)
        pickle_ball = pt.ball_from_pickle(filepath)

        np.testing.assert_allclose(ball.rvw, pickle_ball.rvw)
        np.testing.assert_allclose(ball.s, pickle_ball.s)
        np.testing.assert_allclose(ball.t, pickle_ball.t)
        np.testing.assert_allclose(ball.history.rvw, pickle_ball.history.rvw)
        np.testing.assert_allclose(ball.history.s, pickle_ball.history.s)
        np.testing.assert_allclose(ball.history.t, pickle_ball.history.t)
        np.testing.assert_allclose(ball.history_cts.rvw, pickle_ball.history_cts.rvw)
        np.testing.assert_allclose(ball.history_cts.s, pickle_ball.history_cts.s)
        np.testing.assert_allclose(ball.history_cts.t, pickle_ball.history_cts.t)
