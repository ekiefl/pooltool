#! /usr/bin/env python
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Counter, Generator, List, Optional

import attrs

from pooltool.system.datatypes import System
from pooltool.terminal import Timer
from pooltool.utils.strenum import StrEnum, auto


@attrs.define
class Player:
    name: str

    @classmethod
    def create_players(cls, names: Optional[List[str]] = None) -> List[Player]:
        if names is None:
            names = ["Player 1", "Player 2"]

        assert len(names) == len(set(names)), "Player names must be unique"

        return [cls(name) for name in names]


class Log:
    def __init__(self):
        self.timer = Timer()
        self.msgs = []
        self.update = False

    def add_msg(self, msg, sentiment="neutral", quiet=False) -> None:
        self.msgs.append(
            {
                "time": self.timer.timestamp(),
                "elapsed": self.timer.time_elapsed(fmt="{minutes}:{seconds}"),
                "msg": msg,
                "quiet": quiet,
                "sentiment": sentiment,
                "broadcast": False,
            }
        )

        if not quiet:
            self.update = True


class BallInHandOptions(StrEnum):
    NONE = auto()
    ANYWHERE = auto()
    BEHIND_LINE = auto()


@attrs.define(frozen=True)
class ShotConstraints:
    ball_in_hand: BallInHandOptions
    movable: List
    cueable: List
    hittable: List
    call_shot: bool
    ball_call: Optional[str] = attrs.field(default=None)
    pocket_call: Optional[str] = attrs.field(default=None)


@attrs.define(frozen=True)
class ShotInfo:
    player: Player
    legal: bool
    reason: str
    turn_over: bool
    game_over: bool
    winner: Optional[Player]


class Ruleset(ABC):
    def __init__(self, player_names: Optional[List[str]] = None) -> None:
        # Game progress tracking
        self.score: Counter = Counter()
        self.shot_number: int = 0
        self.turn_number: int = 0

        # Game states
        self.shot_constraints: ShotConstraints = self.initial_shot_constraints()
        self.shot_info: ShotInfo

        # Player info
        self.players: List[Player] = Player.create_players(player_names)
        self.active_idx: int = 0

        self.log: Log = Log()

    @property
    def active_player(self) -> Player:
        return self.players[self.active_idx]

    @property
    def last_player(self) -> Player:
        last_idx = (self.active_idx - 1) % len(self.players)
        return self.players[last_idx]

    def set_next_player(self):
        self.active_idx = self.turn_number % len(self.players)

    def player_order(self) -> Generator[Player, None, None]:
        """Generates player order from current player until last-to-play"""
        for i in range(len(self.players)):
            yield self.players[(self.turn_number + i) % len(self.players)]

    def process_shot(self, shot: System):
        self.shot_info = self.build_shot_info(shot)
        self.log.add_msg(f"{self.shot_info}", sentiment="neutral", quiet=False)

        self.score = self.get_score(shot)
        self.respot_balls(shot)

    def advance(self, shot: System):
        if self.shot_info.game_over:
            if (winner := self.shot_info.winner) is not None:
                self.log.add_msg(f"Game over! {winner.name} wins!", sentiment="good")
            else:
                self.log.add_msg(f"Game over! Tie game!", sentiment="good")
            return

        if self.shot_info.turn_over:
            self.turn_number += 1
        self.shot_number += 1

        self.shot_constraints = self.next_shot_constraints(shot)
        self.set_next_player()

    @abstractmethod
    def build_shot_info(self, shot: System) -> ShotInfo:
        """Build up the essential information about the shot

        The returned ShotInfo is used in conjunction with ShotConstraints to process the
        shot (self.process_shot) and advance the game (self.advance).
        """

    @abstractmethod
    def next_shot_constraints(self, shot: System) -> ShotConstraints:
        pass

    @abstractmethod
    def initial_shot_constraints(self) -> ShotConstraints:
        pass

    @abstractmethod
    def get_score(self, shot: System) -> Counter:
        """Update points

        This method returns a Counter object (like a dictionary) that reflects the
        current score.
        """

    @abstractmethod
    def respot_balls(self, shot: System):
        """Respot balls

        This method should decide which balls should be respotted, and respot them. This
        method should probably make use of pooltool.game.ruleset.utils.respot
        """
