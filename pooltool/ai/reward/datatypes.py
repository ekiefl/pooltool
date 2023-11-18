from typing import Protocol

from pooltool.ai.datatypes import State


class Rewarder(Protocol):
    def calc(self, state: State) -> float:
        ...
