#! /usr/bin/env python
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Counter, Dict, Generator, List, Optional, Tuple

import attrs

import pooltool.constants as c
from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.table.components import Pocket
from pooltool.system.datatypes import System
from pooltool.terminal import Timer
from pooltool.utils.strenum import StrEnum, auto


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


@attrs.define
class ShotInfo:
    shooter: Player
    is_legal: bool
    is_turn_over: bool
    awarded_points: Dict[str, int]


class BallInHandOptions(StrEnum):
    NONE = auto()
    ANYWHERE = auto()
    BEHIND_LINE = auto()


@attrs.define
class ShotConstraints:
    ball_in_hand: BallInHandOptions
    call_shot: bool
    ball_call: Optional[str] = attrs.field(default=None)
    pocket_call: Optional[str] = attrs.field(default=None)


class Ruleset(ABC):
    def __init__(self, player_names: Optional[List[str]] = None) -> None:
        # Game progress tracking
        self.points: Counter = Counter()
        self.shot_number: int = 0
        self.turn_number: int = 0

        # Game states
        self.ball_in_hand: Optional[str] = None
        self.shot_info: ShotInfo
        self.winner: Player
        self.shot_constraints = self.initial_shot_constraints()

        # Boolean indicators
        self.tie: bool = False
        self.game_over = False

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

    def respot(self, shot: System, ball_id: str, x: float, y: float, z: float):
        """Move cue ball to head spot

        Notes
        =====
        - FIXME check if respot position overlaps with ball
        """
        shot.balls[ball_id].state.rvw[0] = [x, y, z]
        shot.balls[ball_id].state.s = c.stationary

    def process_shot(self, shot: System):
        is_legal, reason = self.legality(shot)
        is_turn_over = self.is_turn_over(shot)
        awarded_points = self.award_points(shot)

        self.shot_info = ShotInfo(
            self.active_player,
            is_legal,
            is_turn_over,
            awarded_points,
        )
        self.points += awarded_points

        if not is_legal:
            self.log.add_msg(f"Illegal shot! {reason}", sentiment="bad")

        self.ball_in_hand = self.award_ball_in_hand(shot, is_legal)
        self.respot_balls(shot)

    def advance(self, shot: System):
        if self.is_game_over(shot):
            self.game_over = True
            self.decide_winner(shot)
            self.log.add_msg(f"Game over! {self.winner.name} wins!", sentiment="good")
            return

        if self.shot_info.is_turn_over:
            self.turn_number += 1
        self.shot_number += 1

        self.active_player.ball_in_hand = None
        self.set_next_player()

        if not self.shot_info.is_legal:
            self.active_player.ball_in_hand = self.ball_in_hand

        self.shot_constraints = self.next_shot_constraints(shot)

    @abstractmethod
    def legality(self, shot: System) -> Tuple[bool, str]:
        pass

    @abstractmethod
    def award_points(self, shot: System) -> Counter[str]:
        pass

    @abstractmethod
    def respot_balls(self, shot: System):
        pass

    @abstractmethod
    def is_game_over(self, shot: System) -> bool:
        pass

    @abstractmethod
    def award_ball_in_hand(self, shot: System, legal: bool) -> Optional[str]:
        pass

    @abstractmethod
    def is_turn_over(self, shot: System) -> bool:
        pass

    @abstractmethod
    def decide_winner(self, shot: System):
        pass

    @abstractmethod
    def get_initial_cueing_ball(self, balls) -> Ball:
        pass

    @abstractmethod
    def next_shot_constraints(self, shot: System) -> ShotConstraints:
        pass

    @abstractmethod
    def initial_shot_constraints(self) -> ShotConstraints:
        pass


@attrs.define
class Player:
    name: str
    ball_in_hand: Optional[str] = attrs.field(default=None)

    @classmethod
    def create_players(cls, names: Optional[List[str]] = None) -> List[Player]:
        if names is None:
            names = ["Player 1", "Player 2"]

        assert len(names) == len(set(names)), "Player names must be unique"

        return [cls(name) for name in names]
