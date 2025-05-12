"""The top-level API for the pooltool library

**Important and highly used objects are placed in this top-level API**. For example,
``System`` can be imported directly from the top module:

    >>> import pooltool as pt
    >>> system = pt.System.example()

Alternatively, it can be imported directly from its source location:

    >>> from pooltool.system.datatypes import System
    >>> system = System.example()

If the object you're looking for isn't in this top-level API, **search for it in
the submodules** listed below. Relatedly, if you believe that an objects deserves to
graduate to the top-level API, **your input is valuable** and such changes can be
considered.
"""

# This is a placeholder that is replaced during package building (`poetry build`)
__version__ = "0.0.0"

import pooltool.ai as ai
import pooltool.ai.aim as aim
import pooltool.ai.pot as pot
import pooltool.ani.image as image
import pooltool.constants as constants
import pooltool.events as events
import pooltool.evolution as evolution
import pooltool.game as game
import pooltool.interact as interact
import pooltool.layouts as layouts
import pooltool.objects as objects
import pooltool.physics as physics
import pooltool.ptmath as ptmath
import pooltool.ruleset as ruleset
import pooltool.serialize as serialize
import pooltool.system as system
import pooltool.terminal as terminal
import pooltool.utils as utils
from pooltool.events import EventType
from pooltool.evolution import continuize, interpolate_ball_states, simulate
from pooltool.game.datatypes import GameType
from pooltool.interact import Game, show
from pooltool.layouts import generate_layout, get_rack
from pooltool.objects import (
    Ball,
    BallParams,
    Cue,
    Table,
    TableType,
)
from pooltool.ruleset import Player, get_ruleset
from pooltool.system import MultiSystem, System

__all__ = [
    # subpackages
    "events",
    "evolution",
    "game",
    "objects",
    "physics",
    "ptmath",
    "ruleset",
    "system",
    "utils",
    # submodules
    "constants",
    "interact",
    "layouts",
    # non-documented
    "serialize",
    "terminal",
    "image",
    "ai",
    "pot",
    "aim",
    # objects
    "EventType",
    "GameType",
    "Game",
    "Ball",
    "BallParams",
    "Cue",
    "Table",
    "TableType",
    "Player",
    "MultiSystem",
    "System",
    # functions
    "continuize",
    "interpolate_ball_states",
    "simulate",
    "show",
    "generate_layout",
    "get_rack",
    "get_ruleset",
]
