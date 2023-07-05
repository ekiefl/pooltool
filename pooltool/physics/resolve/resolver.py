from __future__ import annotations

import attrs

from pooltool.events.datatypes import AgentType, Event, EventType
from pooltool.physics.resolve.ball_ball import (
    BallBallCollisionStrategy,
    get_ball_ball_model,
)
from pooltool.physics.resolve.ball_cushion import (
    BallCCushionCollisionStrategy,
    BallLCushionCollisionStrategy,
    get_ball_circ_cushion_model,
    get_ball_lin_cushion_model,
)
from pooltool.physics.resolve.ball_pocket import (
    BallPocketStrategy,
    get_ball_pocket_model,
)
from pooltool.physics.resolve.stick_ball import (
    StickBallCollisionStrategy,
    get_stick_ball_model,
)
from pooltool.physics.resolve.transition import (
    BallTransitionStrategy,
    get_transition_model,
)
from pooltool.system.datatypes import System


@attrs.define
class Resolver:
    ball_ball: BallBallCollisionStrategy
    ball_linear_cushion: BallLCushionCollisionStrategy
    ball_circular_cushion: BallCCushionCollisionStrategy
    ball_pocket: BallPocketStrategy
    stick_ball: StickBallCollisionStrategy
    transition: BallTransitionStrategy

    def resolve(self, shot: System, event: Event) -> None:
        """Resolve an event for a system"""
        _snapshot_initial(shot, event)

        ids = event.ids

        if event.event_type == EventType.NONE:
            return
        elif event.event_type.is_transition():
            ball = shot.balls[ids[0]]
            self.transition.resolve(ball, event.event_type, inplace=True)
        elif event.event_type == EventType.BALL_BALL:
            ball1 = shot.balls[ids[0]]
            ball2 = shot.balls[ids[1]]
            self.ball_ball.resolve(ball1, ball2, inplace=True)
            ball1.state.t = event.time
            ball2.state.t = event.time
        elif event.event_type == EventType.BALL_LINEAR_CUSHION:
            ball = shot.balls[ids[0]]
            cushion = shot.table.cushion_segments.linear[ids[1]]
            self.ball_linear_cushion.resolve(ball, cushion, inplace=True)
            ball.state.t = event.time
        elif event.event_type == EventType.BALL_CIRCULAR_CUSHION:
            ball = shot.balls[ids[0]]
            cushion_jaw = shot.table.cushion_segments.circular[ids[1]]
            self.ball_circular_cushion.resolve(ball, cushion_jaw, inplace=True)
            ball.state.t = event.time
        elif event.event_type == EventType.BALL_POCKET:
            ball = shot.balls[ids[0]]
            pocket = shot.table.pockets[ids[1]]
            self.ball_pocket.resolve(ball, pocket, inplace=True)
            ball.state.t = event.time
        elif event.event_type == EventType.STICK_BALL:
            cue = shot.cue
            ball = shot.balls[ids[1]]
            self.stick_ball.resolve(cue, ball, inplace=True)
            ball.state.t = event.time

        _snapshot_final(shot, event)

    @classmethod
    def default(cls) -> Resolver:
        return cls(
            ball_ball=get_ball_ball_model(),
            ball_linear_cushion=get_ball_lin_cushion_model(),
            ball_circular_cushion=get_ball_circ_cushion_model(),
            ball_pocket=get_ball_pocket_model(),
            stick_ball=get_stick_ball_model(),
            transition=get_transition_model(),
        )


def _snapshot_initial(shot: System, event: Event) -> None:
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


def _snapshot_final(shot: System, event: Event) -> None:
    """Set the final states of the event agents"""
    for agent in event.agents:
        if agent.agent_type == AgentType.BALL:
            agent.set_final(shot.balls[agent.id])
        elif agent.agent_type == AgentType.POCKET:
            agent.set_final(shot.table.pockets[agent.id])
