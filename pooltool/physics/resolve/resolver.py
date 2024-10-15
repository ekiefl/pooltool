"""Resolve collisions and transitions"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import attrs

import pooltool.user_config
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
from pooltool.physics.resolve.types import ModelArgs
from pooltool.serialize import Pathish, conversion
from pooltool.system.datatypes import System
from pooltool.terminal import Run

RESOLVER_CONFIG_PATH = pooltool.user_config.PHYSICS_DIR / "resolver.yaml"
"""The location of the resolver config path YAML."""

VERSION: int = 4


run = Run()


@attrs.define
class ResolverConfig:
    """A structured form of the user resolver config

    Important:
        For everything you need to know about this class, see :doc:`Modular Physics
        </resources/custom_physics>`_.
    """

    ball_ball: BallBallModel
    ball_ball_params: ModelArgs
    ball_linear_cushion: BallLCushionModel
    ball_linear_cushion_params: ModelArgs
    ball_circular_cushion: BallCCushionModel
    ball_circular_cushion_params: ModelArgs
    ball_pocket: BallPocketModel
    ball_pocket_params: ModelArgs
    stick_ball: StickBallModel
    stick_ball_params: ModelArgs
    transition: BallTransitionModel
    transition_params: ModelArgs

    version: Optional[int] = None

    def save(self, path: Pathish) -> Path:
        path = Path(path)
        conversion.unstructure_to(self, path)
        return path

    @classmethod
    def load(cls, path: Pathish) -> ResolverConfig:
        return conversion.structure_from(path, cls)

    @classmethod
    def default(cls) -> ResolverConfig:
        """Load ~/.config/pooltool/physics/resolver.yaml if exists, create otherwise"""
        if RESOLVER_CONFIG_PATH.exists():
            config = cls.load(RESOLVER_CONFIG_PATH)

            if config.version == VERSION:
                return config
            else:
                run.info_single(
                    f"{RESOLVER_CONFIG_PATH} is has version {config.version}, which is not up to "
                    f"date with the most current version: {VERSION}. It will be replaced with the "
                    f"default."
                )

        config = cls(
            ball_ball=BallBallModel.FRICTIONAL_MATHAVAN,
            ball_ball_params={"num_iterations": 1000},
            ball_linear_cushion=BallLCushionModel.HAN_2005,
            ball_linear_cushion_params={},
            ball_circular_cushion=BallCCushionModel.HAN_2005,
            ball_circular_cushion_params={},
            ball_pocket=BallPocketModel.CANONICAL,
            ball_pocket_params={},
            stick_ball=StickBallModel.INSTANTANEOUS_POINT,
            stick_ball_params={"english_throttle": 0.5, "squirt_throttle": 1.0},
            transition=BallTransitionModel.CANONICAL,
            transition_params={},
            version=VERSION,
        )

        config.save(RESOLVER_CONFIG_PATH)
        return config


@attrs.define
class Resolver:
    """A physics engine component that characterizes event resolution

    Important:
        For everything you need to know about this class, see :doc:`Modular Physics
        </resources/custom_physics>`_.
    """

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
        return cls.from_config(ResolverConfig.default())

    @classmethod
    def from_config(cls, config: ResolverConfig) -> Resolver:
        ball_ball = get_ball_ball_model(
            model=config.ball_ball,
            params=config.ball_ball_params,
        )
        ball_linear_cushion = get_ball_lin_cushion_model(
            model=config.ball_linear_cushion,
            params=config.ball_linear_cushion_params,
        )
        ball_circular_cushion = get_ball_circ_cushion_model(
            model=config.ball_circular_cushion,
            params=config.ball_circular_cushion_params,
        )
        ball_pocket = get_ball_pocket_model(
            model=config.ball_pocket,
            params=config.ball_pocket_params,
        )
        stick_ball = get_stick_ball_model(
            model=config.stick_ball,
            params=config.stick_ball_params,
        )
        transition = get_transition_model(
            model=config.transition,
            params=config.transition_params,
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
