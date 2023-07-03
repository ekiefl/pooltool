from __future__ import annotations

import attrs

from pooltool.events.datatypes import AgentType, Event, EventType
from pooltool.physics.resolve import Resolver
from pooltool.physics.resolve.ball_cushion import (
    resolve_circular_ball_cushion,
    resolve_linear_ball_cushion,
)
from pooltool.physics.resolve.ball_pocket import resolve_ball_pocket
from pooltool.physics.resolve.stick_ball import resolve_stick_ball
from pooltool.physics.resolve.transition import resolve_transition
from pooltool.system.datatypes import System


@attrs.define
class PhysicsEngine:
    resolver: Resolver = attrs.field(factory=Resolver.default)

    def snapshot_initial(self, shot: System, event: Event) -> None:
        """Set the initial states of the event agents"""
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

    def snapshot_final(self, shot: System, event: Event) -> None:
        """Set the final states of the event agents"""
        for agent in event.agents:
            if agent.agent_type == AgentType.BALL:
                agent.set_final(shot.balls[agent.id])
            elif agent.agent_type == AgentType.POCKET:
                agent.set_final(shot.table.pockets[agent.id])

    def resolve_event(self, shot: System, event: Event) -> None:
        self.snapshot_initial(shot, event)

        ids = event.ids

        if event.event_type == EventType.NONE:
            return
        elif event.event_type.is_transition():
            ball = shot.balls[ids[0]]
            _ = resolve_transition(ball, event.event_type, inplace=True)
        elif event.event_type == EventType.BALL_BALL:
            ball1 = shot.balls[ids[0]]
            ball2 = shot.balls[ids[1]]
            _ = self.resolver.ball_ball.resolve(ball1, ball2, inplace=True)
            ball1.state.t = event.time
            ball2.state.t = event.time
        elif event.event_type == EventType.BALL_LINEAR_CUSHION:
            ball = shot.balls[ids[0]]
            cushion = shot.table.cushion_segments.linear[ids[1]]
            _ = resolve_linear_ball_cushion(ball, cushion, inplace=True)
            ball.state.t = event.time
        elif event.event_type == EventType.BALL_CIRCULAR_CUSHION:
            ball = shot.balls[ids[0]]
            cushion_jaw = shot.table.cushion_segments.circular[ids[1]]
            _ = resolve_circular_ball_cushion(ball, cushion_jaw, inplace=True)
            ball.state.t = event.time
        elif event.event_type == EventType.BALL_POCKET:
            ball = shot.balls[ids[0]]
            pocket = shot.table.pockets[ids[1]]
            _ = resolve_ball_pocket(ball, pocket, inplace=True)
            ball.state.t = event.time
        elif event.event_type == EventType.STICK_BALL:
            cue = shot.cue
            ball = shot.balls[ids[1]]
            _ = resolve_stick_ball(cue, ball, inplace=True)
            ball.state.t = event.time

        self.snapshot_final(shot, event)
