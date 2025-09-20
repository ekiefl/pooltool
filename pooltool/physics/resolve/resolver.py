"""Resolve collisions and transitions"""

from __future__ import annotations

import shutil
import traceback
from pathlib import Path

import attrs
from cattrs.errors import ClassValidationError

import pooltool.config.paths
from pooltool.events.datatypes import AgentType, Event, EventType
from pooltool.physics.resolve.ball_ball import (
    BallBallCollisionStrategy,
    FrictionalInelastic,
)
from pooltool.physics.resolve.ball_ball.friction import (
    AlciatoreBallBallFriction,
)
from pooltool.physics.resolve.ball_cushion import (
    BallCCushionCollisionStrategy,
    BallLCushionCollisionStrategy,
)
from pooltool.physics.resolve.ball_cushion.mathavan_2010.model import (
    Mathavan2010Circular,
    Mathavan2010Linear,
)
from pooltool.physics.resolve.ball_pocket import (
    BallPocketStrategy,
    CanonicalBallPocket,
)
from pooltool.physics.resolve.ball_table import FrictionalInelasticTable
from pooltool.physics.resolve.ball_table.core import BallTableCollisionStrategy
from pooltool.physics.resolve.serialize import register_serialize_hooks
from pooltool.physics.resolve.stick_ball import (
    StickBallCollisionStrategy,
)
from pooltool.physics.resolve.stick_ball.instantaneous_point import InstantaneousPoint
from pooltool.physics.resolve.transition import (
    BallTransitionStrategy,
    CanonicalTransition,
)
from pooltool.serialize import Pathish, conversion
from pooltool.system.datatypes import System
from pooltool.utils import Run

RESOLVER_PATH = pooltool.config.paths.PHYSICS_DIR / "resolver.yaml"
"""The location of the resolver path YAML."""

VERSION: int = 9


run = Run()


def default_resolver() -> Resolver:
    """The default resolver.

    This default resolver will be used and written to the resolver YAML if:

        1. There is no resolver YAML
        2. The resolver YAML is corrupt
        3. The resolver YAML version doesn't match `VERSION`

    The resolver YAML is found at `RESOLVER_PATH`.
    """
    return Resolver(
        ball_ball=FrictionalInelastic(
            friction=AlciatoreBallBallFriction(
                a=0.009951,
                b=0.108,
                c=1.088,
            ),
        ),
        ball_linear_cushion=Mathavan2010Linear(
            max_steps=1000,
            delta_p=0.001,
        ),
        ball_circular_cushion=Mathavan2010Circular(
            max_steps=1000,
            delta_p=0.001,
        ),
        ball_pocket=CanonicalBallPocket(),
        stick_ball=InstantaneousPoint(
            english_throttle=1.0,
            squirt_throttle=1.0,
        ),
        ball_table=FrictionalInelasticTable(
            min_bounce_height=0.005,
        ),
        transition=CanonicalTransition(),
        version=VERSION,
    )


@attrs.define
class Resolver:
    """A physics engine component that characterizes event resolution

    Important:
        For everything you need to know about this class, see :doc:`Modular Physics
        </resources/custom_physics>`.
    """

    ball_ball: BallBallCollisionStrategy
    ball_linear_cushion: BallLCushionCollisionStrategy
    ball_circular_cushion: BallCCushionCollisionStrategy
    ball_pocket: BallPocketStrategy
    stick_ball: StickBallCollisionStrategy
    ball_table: BallTableCollisionStrategy
    transition: BallTransitionStrategy

    version: int | None = None

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
        elif event.event_type == EventType.BALL_TABLE:
            ball = shot.balls[ids[0]]
            self.ball_table.resolve(ball, inplace=True)
            ball.state.t = event.time

        _snapshot_final(shot, event)

    def save(self, path: Pathish) -> Path:
        path = Path(path)
        conversion.unstructure_to(self, path)
        return path

    @classmethod
    def load(cls, path: Pathish) -> Resolver:
        return conversion.structure_from(path, cls)

    @classmethod
    def default(cls) -> Resolver:
        """Load ~/.config/pooltool/physics/resolver.yaml if exists, create otherwise"""

        if not RESOLVER_PATH.exists():
            resolver = default_resolver()
            resolver.save(RESOLVER_PATH)
            return resolver

        try:
            resolver = cls.load(RESOLVER_PATH)
        except ClassValidationError:
            full_traceback = traceback.format_exc()
            dump_path = RESOLVER_PATH.parent / f".{RESOLVER_PATH.name}"
            run.info(
                f"{RESOLVER_PATH} is malformed and can't be loaded. It is being "
                f"replaced with a default working version. Your version has been moved to "
                f"{dump_path} if you want to diagnose it. Here is the error:\n{full_traceback}",
                style="red",
            )
            shutil.move(RESOLVER_PATH, dump_path)
            resolver = default_resolver()
            resolver.save(RESOLVER_PATH)

        if resolver.version == VERSION:
            return resolver
        else:
            dump_path = RESOLVER_PATH.parent / f".{RESOLVER_PATH.name}"
            run.info(
                f"{RESOLVER_PATH} has version {resolver.version}, which is not up to "
                f"date with the most current version: {VERSION}. It will be replaced with the "
                f"default. Your version has been moved to {dump_path}.",
                style="yellow",
            )
            shutil.move(RESOLVER_PATH, dump_path)
            resolver = default_resolver()
            resolver.save(RESOLVER_PATH)
            return resolver


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


register_serialize_hooks()
