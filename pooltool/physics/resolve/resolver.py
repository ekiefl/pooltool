from __future__ import annotations

from pathlib import Path
from typing import Dict, Union

import attrs

from pooltool.events.datatypes import AgentType, Event, EventType
from pooltool.physics.resolve.ball_ball import (
    BallBallCollisionStrategy,
    BallBallModel,
    get_ball_ball_model,
)
from pooltool.physics.resolve.ball_cushion import (
    BallCCushionCollisionStrategy,
    BallCCushionModel,
    BallLCushionCollisionStrategy,
    BallLCushionModel,
    get_ball_circ_cushion_model,
    get_ball_lin_cushion_model,
)
from pooltool.physics.resolve.ball_pocket import (
    BallPocketModel,
    BallPocketStrategy,
    get_ball_pocket_model,
)
from pooltool.physics.resolve.stick_ball import (
    StickBallCollisionStrategy,
    StickBallModel,
    get_stick_ball_model,
)
from pooltool.physics.resolve.transition import (
    BallTransitionModel,
    BallTransitionStrategy,
    get_transition_model,
)
from pooltool.serialize import Pathish, conversion
from pooltool.system.datatypes import System

ArgType = Union[float, int, str, bool]
ModelArgs = Dict[str, ArgType]

# Leave type-casting to the JSON/YAML serializer
conversion.register_structure_hook(cl=ArgType, func=lambda d, t: d)


@attrs.define
class ResolverConfig:
    ball_ball: BallBallModel
    ball_ball_kwargs: ModelArgs

    ball_linear_cushion: BallLCushionModel
    ball_linear_cushion_kwargs: ModelArgs

    ball_circular_cushion: BallCCushionModel
    ball_circular_cushion_kwargs: ModelArgs

    ball_pocket: BallPocketModel
    ball_pocket_kwargs: ModelArgs

    stick_ball: StickBallModel
    stick_ball_kwargs: ModelArgs

    transition: BallTransitionModel
    transition_kwargs: ModelArgs

    @classmethod
    def load(cls, path: Pathish) -> ResolverConfig:
        return conversion.structure_from(path, cls)

    def save(self, path: Pathish) -> Path:
        path = Path(path)
        conversion.unstructure_to(self, path)
        return path


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

    @classmethod
    def from_config(cls, config: ResolverConfig) -> Resolver:
        ball_ball = get_ball_ball_model(
            model=config.ball_ball,
            **config.ball_ball_kwargs,
        )

        ball_linear_cushion = get_ball_lin_cushion_model(
            model=config.ball_linear_cushion,
            **config.ball_linear_cushion_kwargs,
        )

        ball_circular_cushion = get_ball_circ_cushion_model(
            model=config.ball_circular_cushion,
            **config.ball_circular_cushion_kwargs,
        )

        ball_pocket = get_ball_pocket_model(
            model=config.ball_pocket,
            **config.ball_pocket_kwargs,
        )

        stick_ball = get_stick_ball_model(
            model=config.stick_ball,
            **config.stick_ball_kwargs,
        )

        transition = get_transition_model(
            model=config.transition,
            **config.transition_kwargs,
        )

        return cls(
            ball_ball,
            ball_linear_cushion,
            ball_circular_cushion,
            ball_pocket,
            stick_ball,
            transition,
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
