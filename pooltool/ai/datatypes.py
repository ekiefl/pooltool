import attrs

from pooltool.game.ruleset.datatypes import Ruleset
from pooltool.system.datatypes import System


@attrs.define
class State:
    system: System
    game: Ruleset
