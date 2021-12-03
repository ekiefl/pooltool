#! /usr/bin/env python

import pooltool as pt

from pooltool.tests import *
from pooltool.error import ConfigError
from pooltool.objects.ball import Ball

import pytest
import numpy as np
import tempfile


def test_bad_id():
    with pytest.raises(ConfigError):
        Ball(234.2)


def test_set(sliding_ball):
    rvw, s, t = np.array(np.random.rand(9).reshape((3,3))), 0, 0.2341
    sliding_ball.set(rvw, s, t)
    np.testing.assert_allclose(sliding_ball.rvw, rvw)
    np.testing.assert_allclose(sliding_ball.s, s)
    np.testing.assert_allclose(sliding_ball.t, t)


def test_save(sliding_ball):
    file = tempfile.NamedTemporaryFile()
    filepath = file.name

    sliding_ball.save(filepath)
    pickle_ball = pt.ball_from_dict(pt.utils.load_pickle(filepath))

    np.testing.assert_allclose(sliding_ball.rvw, pickle_ball.rvw)
    np.testing.assert_allclose(sliding_ball.s, pickle_ball.s)
    np.testing.assert_allclose(sliding_ball.t, pickle_ball.t)


def test_update_next_transition_event(sliding_ball, rolling_ball, spinning_ball, stationary_ball, pocketed_ball):
    sliding_ball.update_next_transition_event()
    np.testing.assert_allclose(sliding_ball.next_transition_event.time, 0.32041931624490966)

    rolling_ball.update_next_transition_event()
    np.testing.assert_allclose(rolling_ball.next_transition_event.time, 15.457626173646455)

    spinning_ball.update_next_transition_event()
    np.testing.assert_allclose(spinning_ball.next_transition_event.time, 2.7494110320409817)

    stationary_ball.update_next_transition_event()
    assert np.isinf(stationary_ball.next_transition_event.time)

    pocketed_ball.update_next_transition_event()
    assert np.isinf(pocketed_ball.next_transition_event.time)








