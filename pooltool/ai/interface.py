from typing import Protocol

from pooltool.ai.datatypes import Action
from pooltool.system.datatypes import System


class AIPlayer(Protocol):
    def decide(self, system: System) -> Action:
        ...

    def apply(self, system: System, action: Action) -> None:
        ...
