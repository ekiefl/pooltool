import numpy as np

import pooltool.constants as c
import pooltool.physics as physics
import pooltool.utils as utils


def resolve_ball_ball(event):
    event.assert_not_partial()
    ball1, ball2 = event.agents

    rvw1, rvw2 = physics.resolve_ball_ball_collision(ball1.rvw, ball2.rvw)
    s1, s2 = c.sliding, c.sliding

    ball1.set(rvw1, s1, t=event.time)
    ball1.update_next_transition_event()

    ball2.set(rvw2, s2, t=event.time)
    ball2.update_next_transition_event()

    event.final_states = [
        (np.copy(ball1.rvw), ball1.s),
        (np.copy(ball2.rvw), ball2.s),
    ]


def resolve_null(event):
    event.assert_not_partial()


def resolve_ball_cushion(event):
    event.assert_not_partial()
    ball, cushion = event.agents
    normal = cushion.get_normal(ball.rvw)

    rvw = physics.resolve_ball_cushion_collision(
        rvw=ball.rvw,
        normal=normal,
        R=ball.R,
        m=ball.m,
        h=cushion.height,
        e_c=ball.e_c,
        f_c=ball.f_c,
    )
    s = c.sliding

    ball.set(rvw, s, t=event.time)
    ball.update_next_transition_event()

    event.final_states = [
        (np.copy(ball.rvw), ball.s),
        None,
    ]


def resolve_ball_pocket(event):
    event.assert_not_partial()
    ball, pocket = event.agents

    # Ball is placed at the pocket center
    rvw = np.array([[pocket.a, pocket.b, -pocket.depth], [0, 0, 0], [0, 0, 0]])

    ball.set(rvw, c.pocketed)
    ball.update_next_transition_event()

    pocket.add(ball.id)

    event.final_states = [
        (np.copy(ball.rvw), ball.s),
        None,
    ]


def resolve_stick_ball(event):
    event.assert_not_partial()
    cue_stick, ball = event.agents

    v, w = physics.cue_strike(
        ball.m,
        cue_stick.M,
        ball.R,
        cue_stick.V0,
        cue_stick.phi,
        cue_stick.theta,
        cue_stick.a,
        cue_stick.b,
    )
    rvw = np.array([ball.rvw[0], v, w])

    s = (
        c.rolling
        if abs(np.sum(utils.get_rel_velocity_fast(rvw, ball.R))) <= c.tol
        else c.sliding
    )

    ball.set(rvw, s)
    ball.update_next_transition_event()

    event.final_states = [
        (np.copy(ball.rvw), ball.s),
        None,
    ]


def resolve_transition(event):
    event.assert_not_partial()

    start, end = event.event_type.ball_transition_motion_states()

    ball = event.agents[0]
    ball.s = end
    ball.update_next_transition_event()

    event.final_states = [(np.copy(ball.rvw), end)]
