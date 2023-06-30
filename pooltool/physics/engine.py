from __future__ import annotations

from typing import Callable, Dict, Tuple

import attrs
import numpy as np

import pooltool.constants as c
import pooltool.physics as physics
from pooltool.events.datatypes import AgentType, Event, EventType
from pooltool.objects.ball.datatypes import Ball, BallState
from pooltool.objects.cue.datatypes import Cue
from pooltool.objects.table.components import (
    CircularCushionSegment,
    LinearCushionSegment,
    Pocket,
)
from pooltool.system.datatypes import System


def resolve_ball_ball(event: Event) -> Event:
    ball1, ball2 = event.agents

    assert isinstance(ball1.initial, Ball)
    assert isinstance(ball2.initial, Ball)

    rvw1, rvw2 = physics.resolve_ball_ball_collision(
        ball1.initial.state.rvw.copy(),
        ball2.initial.state.rvw.copy(),
        ball1.initial.params.R,
    )

    ball1.final = attrs.evolve(
        ball1.initial, state=BallState(rvw1, c.sliding, event.time)
    )
    ball2.final = attrs.evolve(
        ball2.initial, state=BallState(rvw2, c.sliding, event.time)
    )

    return event


def resolve_null(event: Event) -> Event:
    return event


def resolve_linear_ball_cushion(event: Event) -> Event:
    ball, cushion = event.agents

    assert isinstance(ball.initial, Ball)
    assert isinstance(cushion.initial, LinearCushionSegment)

    rvw = ball.initial.state.rvw
    normal = cushion.initial.get_normal(rvw)

    rvw = physics.resolve_ball_linear_cushion_collision(
        rvw=rvw,
        normal=normal,
        p1=cushion.initial.p1,
        p2=cushion.initial.p2,
        R=ball.initial.params.R,
        m=ball.initial.params.m,
        h=cushion.initial.height,
        e_c=ball.initial.params.e_c,
        f_c=ball.initial.params.f_c,
    )

    ball.final = attrs.evolve(ball.initial, state=BallState(rvw, c.sliding, event.time))
    cushion.final = None

    return event


def resolve_circular_ball_cushion(event: Event) -> Event:
    ball, cushion = event.agents

    assert isinstance(ball.initial, Ball)
    assert isinstance(cushion.initial, CircularCushionSegment)

    rvw = ball.initial.state.rvw
    normal = cushion.initial.get_normal(rvw)

    rvw = physics.resolve_ball_circular_cushion_collision(
        rvw=rvw,
        normal=normal,
        center=cushion.initial.center,
        radius=cushion.initial.radius,
        R=ball.initial.params.R,
        m=ball.initial.params.m,
        h=cushion.initial.height,
        e_c=ball.initial.params.e_c,
        f_c=ball.initial.params.f_c,
    )

    ball.final = attrs.evolve(ball.initial, state=BallState(rvw, c.sliding, event.time))
    cushion.final = None

    return event


def resolve_ball_pocket(event: Event) -> Event:
    ball, pocket = event.agents

    assert isinstance(ball.initial, Ball)
    assert isinstance(pocket.initial, Pocket)

    # Ball is placed at the pocket center
    rvw = np.array(
        [
            [pocket.initial.a, pocket.initial.b, -pocket.initial.depth],
            [0, 0, 0],
            [0, 0, 0],
        ]
    )

    ball.final = attrs.evolve(
        ball.initial, state=BallState(rvw, c.pocketed, event.time)
    )
    pocket.final = pocket.initial.copy()
    pocket.final.add(ball.final.id)

    return event


def resolve_stick_ball(event: Event) -> Event:
    cue, ball = event.agents

    assert isinstance(ball.initial, Ball)
    assert isinstance(cue.initial, Cue)

    v, w = physics.cue_strike(
        ball.initial.params.m,
        cue.initial.specs.M,
        ball.initial.params.R,
        cue.initial.V0,
        cue.initial.phi,
        cue.initial.theta,
        cue.initial.a,
        cue.initial.b,
    )

    rvw = np.array([ball.initial.state.rvw[0], v, w])
    s = c.sliding

    ball.final = attrs.evolve(ball.initial, state=BallState(rvw, s, event.time))
    cue.final = None

    return event


def resolve_transition(event: Event) -> Event:
    ball = event.agents[0]

    assert isinstance(ball.initial, Ball)

    start, end = _ball_transition_motion_states(event.event_type)

    ball.final = ball.initial.copy()
    ball.final.state.s = end
    ball.initial.state.s = start

    if end == c.spinning:
        # Assert that the velocity components are nearly 0, and that the x and y angular
        # velocity components are nearly 0. Then set them to exactly 0.
        v = ball.final.state.rvw[1]
        w = ball.final.state.rvw[2]
        assert (np.abs(v) < c.EPS_SPACE).all()
        assert (np.abs(w[:2]) < c.EPS_SPACE).all()

        ball.final.state.rvw[1, :] = [0.0, 0.0, 0.0]
        ball.final.state.rvw[2, :2] = [0.0, 0.0]

    if end == c.stationary:
        # Assert that the linear and angular velocity components are nearly 0, then set
        # them to exactly 0.
        v = ball.final.state.rvw[1]
        w = ball.final.state.rvw[2]
        assert (np.abs(v) < c.EPS_SPACE).all()
        assert (np.abs(w) < c.EPS_SPACE).all()

        ball.final.state.rvw[1, :] = [0.0, 0.0, 0.0]
        ball.final.state.rvw[2, :] = [0.0, 0.0, 0.0]

    return event


def _ball_transition_motion_states(event_type: EventType) -> Tuple[int, int]:
    """Return the ball motion states before and after a transition"""
    assert event_type.is_transition()

    if event_type == EventType.SPINNING_STATIONARY:
        return c.spinning, c.stationary
    elif event_type == EventType.ROLLING_STATIONARY:
        return c.rolling, c.stationary
    elif event_type == EventType.ROLLING_SPINNING:
        return c.rolling, c.spinning
    elif event_type == EventType.SLIDING_ROLLING:
        return c.sliding, c.rolling

    raise NotImplementedError()


@attrs.define
class Resolver:
    null: Callable
    ball_ball: Callable
    ball_linear_cushion: Callable
    ball_circular_cushion: Callable
    ball_pocket: Callable
    stick_ball: Callable
    transition: Callable

    mapping: Dict[EventType, Callable] = attrs.field(init=False)

    def __attrs_post_init__(self):
        self.mapping = {
            EventType.NONE: self.null,
            EventType.BALL_BALL: self.ball_ball,
            EventType.BALL_LINEAR_CUSHION: self.ball_linear_cushion,
            EventType.BALL_CIRCULAR_CUSHION: self.ball_circular_cushion,
            EventType.BALL_POCKET: self.ball_pocket,
            EventType.STICK_BALL: self.stick_ball,
            EventType.SPINNING_STATIONARY: self.transition,
            EventType.ROLLING_STATIONARY: self.transition,
            EventType.ROLLING_SPINNING: self.transition,
            EventType.SLIDING_ROLLING: self.transition,
        }

    @classmethod
    def default(cls) -> Resolver:
        return cls(
            null=resolve_null,
            ball_ball=resolve_ball_ball,
            ball_linear_cushion=resolve_linear_ball_cushion,
            ball_circular_cushion=resolve_circular_ball_cushion,
            ball_pocket=resolve_ball_pocket,
            stick_ball=resolve_stick_ball,
            transition=resolve_transition,
        )


@attrs.define
class PhysicsEngine:
    resolver: Resolver = attrs.field(factory=Resolver.default)

    def resolve_event(self, shot: System, event: Event) -> None:
        if event.event_type == EventType.NONE:
            return

        # The system has evolved since the event was created, so the initial states need
        # to be snapshotted according to the current state
        for agent in event.agents:
            if agent.agent_type == AgentType.CUE:
                agent.set_initial(shot.cue)
            elif agent.agent_type == AgentType.BALL:
                agent.set_initial(shot.balls[agent.id])
            elif agent.agent_type == AgentType.POCKET:
                agent.set_initial(shot.table.pockets[agent.id])
            elif agent.agent_type == AgentType.LINEAR_CUSHION_SEGMENT:
                agent.set_initial(shot.table.cushion_segments.linear[agent.id])
            elif agent.agent_type == AgentType.CIRCULAR_CUSHION_SEGMENT:
                agent.set_initial(shot.table.cushion_segments.circular[agent.id])

        event = self.resolver.mapping[event.event_type](event)

        # The final states of the agents are solved, but the system objects still need
        # to be updated with these states.
        for agent in event.agents:
            final = agent.get_final()
            if isinstance(final, Ball):
                shot.balls[final.id].state = final.state
            elif isinstance(final, Pocket):
                shot.table.pockets[final.id] = final
