#! /usr/bin/env python

import pooltool.events as e
from pooltool.tests import *
from pooltool.objects.ball import Ball


def test_ball_ball(ball_ball_collision_pack):
    ball_1, ball_2, ball_1_expected_rvw, ball_2_expected_rvw = ball_ball_collision_pack

    event = e.BallBallCollision(ball_1, ball_2)
    event.resolve()

    np.testing.assert_allclose(event.ball1_state_end[0], ball_1_expected_rvw)
    np.testing.assert_allclose(ball_1.rvw, ball_1_expected_rvw)

    np.testing.assert_allclose(event.ball2_state_end[0], ball_2_expected_rvw)
    np.testing.assert_allclose(ball_2.rvw, ball_2_expected_rvw)


