#! /usr/bin/env python

import pooltool.physics as p

from pooltool.tests import *

def test_get_rel_velocity(sliding_ball, rolling_ball, spinning_ball, stationary_ball, pocketed_ball):
    ans = p.get_rel_velocity(sliding_ball.rvw, sliding_ball.R)
    np.testing.assert_allclose(ans, np.array([0.0703005532, -0.3504767645, 0.]))

    ans = p.get_rel_velocity(rolling_ball.rvw, rolling_ball.R)
    np.testing.assert_allclose(ans, np.zeros(3), atol=1e-7)

    ans = p.get_rel_velocity(spinning_ball.rvw, spinning_ball.R)
    np.testing.assert_allclose(ans, np.zeros(3), atol=1e-7)

    ans = p.get_rel_velocity(stationary_ball.rvw, stationary_ball.R)
    np.testing.assert_allclose(ans, np.zeros(3), atol=1e-7)

    ans = p.get_rel_velocity(pocketed_ball.rvw, pocketed_ball.R)
    np.testing.assert_allclose(ans, np.zeros(3), atol=1e-7)


def test_resolve_ball_ball_collision(ball_ball_collision_pack):
    b1, b2, b1_expected_rvw, b2_expected_rvw = ball_ball_collision_pack

    b1_rvw, b2_rvw = p.resolve_ball_ball_collision(b1.rvw, b2.rvw)

    np.testing.assert_allclose(b1_rvw, b1_expected_rvw)
    np.testing.assert_allclose(b2_rvw, b2_expected_rvw)


def test_resolve_ball_cushion_collision(ball_cushion_collision_pack):
    ball, cushion, expected_rvw = ball_cushion_collision_pack
    rvw = p.resolve_ball_cushion_collision(ball.rvw, cushion.normal, ball.R, ball.m, cushion.height)
    np.testing.assert_allclose(rvw, expected_rvw)
