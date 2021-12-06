#! /usr/bin/env python
"""Unit testing for physics.py

Most of the unit tests in this module work differently than one might expect. Rather than feed each
physics equation a series of carefully crafted examples where the expected answer is calculated by
hand, instead I search for existing examples of the physics equation being used within the benchmark
shot.  Since the benchmark shot is assumed to be the truth, I can test whether the function in the
current codebase returns the identical output to that in the benchmark shot.

The advantages of this approach is that (1) the tests require very little upkeep and (2) a large
breadth of circumstances are tested for each physics equation. For example, at the time of writing
this, the benchmark shot contains 18 ball-ball collisions, so physics.resolve_ball_ball_collision is
tested under 18 non-trivial circumstances.

The disadvantage to this approach is that truth is defined relative to the benchmark shot. If the
benchmark shot contains incorrect functionality, then these tests serve no purpose in ensuring
absolute truth. With this in mind, these unit tests are not designed to prove correctness, but
rather to preserve functionality in the face of any refactoring that takes place.
"""

import pooltool.physics as p
import pooltool.constants as c

from pooltool.tests import trial, ref

import numpy as np


def test_resolve_ball_ball_collision(ref):
    collision_events = ref.events.filter_type('ball-ball')

    for col in collision_events:
        ball1, ball2 = col.agents

        # Set agents to their pre-resolved states
        ball1.rvw, ball1.s = col.agent1_state_initial
        ball2.rvw, ball2.s = col.agent2_state_initial

        # Store the expected post-resolved states. These were the values
        # calculated from the reference benchmark, which we assume to be
        # the correct values
        ball1_rvw_expected, ball1_s_expected = np.copy(col.agent1_state_final[0]), col.agent1_state_final[1]
        ball2_rvw_expected, ball2_s_expected = np.copy(col.agent2_state_final[0]), col.agent2_state_final[1]

        # Now resolve the event with the current codebase
        col.resolve()
        ball1_rvw, ball1_s = col.agent1_state_final
        ball2_rvw, ball2_s = col.agent2_state_final

        # Assert the calculated values equal the reference values
        np.testing.assert_allclose(ball1_rvw, ball1_rvw_expected)
        np.testing.assert_allclose(ball1_s, ball1_s_expected)
        np.testing.assert_allclose(ball2_rvw, ball2_rvw_expected)
        np.testing.assert_allclose(ball2_s, ball2_s_expected)


def test_resolve_ball_cushion_collision(ref):
    collision_events = ref.events.filter_type('ball-cushion')

    for col in collision_events:
        ball, cushion = col.agents

        # Set agents to their pre-resolved states
        ball.rvw, ball.s = col.agent1_state_initial

        # Store the expected post-resolved states. These were the values
        # calculated from the reference benchmark, which we assume to be
        # the correct values
        ball_rvw_expected, ball_s_expected = np.copy(col.agent1_state_final[0]), col.agent1_state_final[1]

        # Now resolve the event with the current codebase
        col.resolve()
        ball_rvw, ball_s = col.agent1_state_final

        np.testing.assert_allclose(ball_rvw, ball_rvw_expected)
        np.testing.assert_allclose(ball_s, ball_s_expected)


def test_get_ball_ball_collision_time(ref):
    for i, event in enumerate(ref.events):
        if event.event_type == 'ball-ball':
            prev_event = ref.events[i-1]

            t_expected = event.time - prev_event.time

            # Set ball states to previous event state
            ball1, ball2 = event.agents
            ball1.set_from_history(i-1)
            ball2.set_from_history(i-1)

            # Calculate time until collision
            t = p.get_ball_ball_collision_time(
                rvw1 = ball1.rvw,
                rvw2 = ball2.rvw,
                s1 = ball1.s,
                s2 = ball2.s,
                mu1 = ball1.u_s if ball1.s == c.sliding else ball1.u_r,
                mu2 = ball2.u_s if ball2.s == c.sliding else ball2.u_r,
                m1 = ball1.m,
                m2 = ball2.m,
                g1 = ball1.g,
                g2 = ball2.g,
                R = ball1.R
            )

            np.testing.assert_allclose(t, t_expected)


def test_get_ball_linear_cushion_collision_time(ref):
    for i, event in enumerate(ref.events):
        if event.event_type == 'ball-cushion':
            ball, cushion = event.agents

            if cushion.object_type != 'linear_cushion_segment':
                continue

            prev_event = ref.events[i-1]
            t_expected = event.time - prev_event.time

            ball.set_from_history(i-1)

            t = p.get_ball_linear_cushion_collision_time(
                rvw=ball.rvw,
                s=ball.s,
                lx=cushion.lx,
                ly=cushion.ly,
                l0=cushion.l0,
                p1=cushion.p1,
                p2=cushion.p2,
                mu=(ball.u_s if ball.s == c.sliding else ball.u_r),
                m=ball.m,
                g=ball.g,
                R=ball.R
            )

            np.testing.assert_allclose(t, t_expected)


def test_get_ball_circular_cushion_collision_time(ref):
    for i, event in enumerate(ref.events):
        if event.event_type == 'ball-cushion':
            ball, cushion = event.agents

            if cushion.object_type != 'circular_cushion_segment':
                continue

            prev_event = ref.events[i-1]
            t_expected = event.time - prev_event.time

            ball.set_from_history(i-1)

            t = p.get_ball_circular_cushion_collision_time(
                rvw=ball.rvw,
                s=ball.s,
                a=cushion.a,
                b=cushion.b,
                r=cushion.radius,
                mu=(ball.u_s if ball.s == c.sliding else ball.u_r),
                m=ball.m,
                g=ball.g,
                R=ball.R
            )

            np.testing.assert_allclose(t, t_expected)


def test_get_ball_pocket_collision_time(ref):
    for i, event in enumerate(ref.events):
        if event.event_type == 'ball-pocket':
            ball, pocket = event.agents

            prev_event = ref.events[i-1]
            t_expected = event.time - prev_event.time

            ball.set_from_history(i-1)

            t = p.get_ball_pocket_collision_time(
                rvw=ball.rvw,
                s=ball.s,
                a=pocket.a,
                b=pocket.b,
                r=pocket.radius,
                mu=(ball.u_s if ball.s == c.sliding else ball.u_r),
                m=ball.m,
                g=ball.g,
                R=ball.R
            )

            np.testing.assert_allclose(t, t_expected)


