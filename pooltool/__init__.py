"""The top-level API for the pooltool library.

Important and highly used objects are placed in this top-level API. For example,
``System`` can be imported directly from the top module:

    >>> import pooltool as pt
    >>> system = pt.System.example()

Alternatively, it can be imported directly from its lower-level API location:

    >>> from pooltool.system import System
    >>> system = System.example()

If the object you're looking for isn't in this top-level API, **search for it in
the subpackages/submodules** listed below. Relatedly, if you believe that an objects deserves to
graduate to the top-level API, **your input is valuable** and such changes can be
considered.
"""

from importlib.metadata import version

__version__ = version("pooltool-billiards")

from pooltool import (
    ai,
    constants,
    events,
    evolution,
    game,
    interact,
    layouts,
    objects,
    physics,
    ptmath,
    ruleset,
    serialize,
    system,
    utils,
)
from pooltool.ai import aim, pot
from pooltool.ani import image
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
    "Ball",
    "BallParams",
    "Cue",
    "EventType",
    "Game",
    "GameType",
    "MultiSystem",
    "Player",
    "System",
    "Table",
    "TableType",
    "ai",
    "aim",
    "constants",
    "continuize",
    "events",
    "evolution",
    "game",
    "generate_layout",
    "get_rack",
    "get_ruleset",
    "image",
    "interact",
    "interpolate_ball_states",
    "layouts",
    "objects",
    "physics",
    "pot",
    "ptmath",
    "ruleset",
    "serialize",
    "show",
    "simulate",
    "system",
    "utils",
]
