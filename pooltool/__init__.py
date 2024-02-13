"""The primary interface for the pooltool library

Members on this page have been chosen to selectively capture the most common /
expected use cases of pooltool, and can be used simply by importing the ``pooltool``
package. For instance:

    >>> import pooltool as pt
    >>> ball = pt.Ball("cue")

Note:
    You can of course, also import ``Ball`` from it's source
    (:class:`pooltool.objects.ball.datatypes.Ball`):

        >>> from pooltool.objects.ball.datatypes import Ball

There are many other components of pooltool's API that can also be accessed, but
that require a more detailed importing. As just an example:

    >>> from pooltool.physics.resolve.ball_cushion.han_2005 import model

If you believe that a component deserves to graduate to the top-level API, your
input is valuable and such changes can be considered.
"""

__version__ = "0.2.2.1-dev"

import pooltool.ai as ai
import pooltool.ai.aim as aim
import pooltool.ai.pot as pot
from pooltool import terminal
from pooltool.ani.animate import FrameStepper, Game, ShotViewer
from pooltool.ani.image import (
    GzipArrayImages,
    HDF5Images,
    ImageZip,
    NpyImages,
    image_stack,
    save_images,
)
from pooltool.events import (
    Agent,
    AgentType,
    Event,
    EventType,
    ball_ball_collision,
    ball_circular_cushion_collision,
    ball_linear_cushion_collision,
    ball_pocket_collision,
    by_ball,
    by_time,
    by_type,
    filter_ball,
    filter_events,
    filter_time,
    filter_type,
    null_event,
    rolling_spinning_transition,
    rolling_stationary_transition,
    sliding_rolling_transition,
    spinning_stationary_transition,
    stick_ball_collision,
)
from pooltool.evolution import simulate
from pooltool.evolution.continuize import continuize
from pooltool.game.datatypes import GameType
from pooltool.game.layouts import generate_layout, get_rack
from pooltool.game.ruleset import (
    EightBall,
    NineBall,
    Snooker,
    SumToThree,
    ThreeCushion,
    get_ruleset,
)
from pooltool.game.ruleset.datatypes import Player, Ruleset
from pooltool.objects import (
    Ball,
    BallHistory,
    BallOrientation,
    BallParams,
    BallSet,
    BallState,
    BilliardTableSpecs,
    CircularCushionSegment,
    Cue,
    CueSpecs,
    CushionDirection,
    CushionSegments,
    LinearCushionSegment,
    Pocket,
    PocketTableSpecs,
    SnookerTableSpecs,
    Table,
    TableModelDescr,
    TableType,
    get_ballset,
)
from pooltool.physics.engine import PhysicsEngine
from pooltool.system import MultiSystem, System, SystemController, multisystem, visual

run = terminal.Run()
progress = terminal.Progress()


__all__ = [
    "System",
    "MultiSystem",
    "PhysicsEngine",
    "multisystem",
    "SystemController",
    "visual",
    "filter_ball",
    "filter_time",
    "filter_type",
    "filter_events",
    "by_type",
    "by_ball",
    "by_time",
    "FrameStepper",
    "null_event",
    "ball_ball_collision",
    "ball_linear_cushion_collision",
    "ball_circular_cushion_collision",
    "ball_pocket_collision",
    "stick_ball_collision",
    "spinning_stationary_transition",
    "rolling_stationary_transition",
    "rolling_spinning_transition",
    "sliding_rolling_transition",
    "GameType",
    "Event",
    "EventType",
    "AgentType",
    "Agent",
    "Ball",
    "BallSet",
    "BallState",
    "BallParams",
    "BallHistory",
    "BallOrientation",
    "CueSpecs",
    "Cue",
    "Pocket",
    "LinearCushionSegment",
    "CircularCushionSegment",
    "CushionSegments",
    "CushionDirection",
    "ImageZip",
    "HDF5Images",
    "GzipArrayImages",
    "NpyImages",
    "Table",
    "TableModelDescr",
    "TableType",
    "PocketTableSpecs",
    "BilliardTableSpecs",
    "SnookerTableSpecs",
    "Game",
    "save_images",
    "image_stack",
    "ShotViewer",
    "simulate",
    "continuize",
    "get_rack",
    "generate_layout",
    "get_ruleset",
    "ThreeCushion",
    "EightBall",
    "Player",
    "NineBall",
    "Ruleset",
    "SumToThree",
    "Snooker",
    "get_ballset",
    "ai",
    "pot",
    "aim",
]
