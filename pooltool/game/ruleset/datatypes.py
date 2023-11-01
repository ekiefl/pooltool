#! /usr/bin/env python
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Counter, Dict, Generator, List, Optional, Set, Tuple

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


class BallInHandOptions(StrEnum):
    NONE = auto()
    ANYWHERE = auto()
    BEHIND_LINE = auto()


@attrs.define
class ShotConstraints:
    ball_in_hand: BallInHandOptions
    movable: Set
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
        self.winner: Player
        self.shot_constraints = self.initial_shot_constraints()

        # Boolean indicators
        self.tie: bool = False  # FIXME code this during game over screen
        self.game_over: bool = False

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
        """FIXME this is a utils.py fn

        Notes
        =====
        - FIXME check if respot position overlaps with ball
        """
        shot.balls[ball_id].state.rvw[0] = [x, y, z]
        shot.balls[ball_id].state.s = c.stationary

    def process_shot(self, shot: System):
        is_legal, reason = self.legality(shot)
        awarded_points = self.award_points(shot)
        self.points += awarded_points

        if is_legal and reason != "":
            self.log.add_msg(f"Legal shot! {reason}", sentiment="good")
        elif not is_legal:
            self.log.add_msg(f"Illegal shot! {reason}", sentiment="bad")

        self.respot_balls(shot)

    def advance(self, shot: System):
        if self.is_game_over(shot):
            self.game_over = True
            self.decide_winner(shot)
            self.log.add_msg(f"Game over! {self.winner.name} wins!", sentiment="good")
            return

        if self.is_turn_over(shot):
            self.turn_number += 1
        self.shot_number += 1

        self.set_next_player()

        self.shot_constraints = self.next_shot_constraints(shot)

    @abstractmethod
    def legality(self, shot: System) -> Tuple[bool, str]:
        """Is the shot legal?

        This method should return whether or not the shot was legal, and a string
        indicating the reason. If the shot was legal, it makes sense to return an empty
        string for the reason.
        """
        pass

    @abstractmethod
    def is_turn_over(self, shot: System) -> bool:
        """Is the player's turn over?

        This method returns whether or not the player's turn is over
        """
        pass

    @abstractmethod
    def award_points(self, shot: System) -> None:
        """Update points

        This method should update self.points to reflect the new score. self.points is a
        Counter object (like a dictionary).
        """
        pass

    @abstractmethod
    def respot_balls(self, shot: System):
        """Respot balls

        This method should decide which balls should be respotted, and respot them. This
        method should probably make use of pooltool.game.ruleset.utils.respot
        """
        pass

    @abstractmethod
    def is_game_over(self, shot: System) -> bool:
        """Determine whether the game is over

        Returns whether or not the game is finished.
        """
        pass

    @abstractmethod
    def decide_winner(self, shot: System):
        """Decide the winner

        This method should modify the self.winner attribute, setting it to be the player
        who wins. This method is only called when self.is_game_over returns True.
        """
        pass

    @abstractmethod
    def get_initial_cueing_ball(self, balls) -> Ball:
        """FIXME remove (use cueable attribute for ShotConstraints)"""
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

    @classmethod
    def create_players(cls, names: Optional[List[str]] = None) -> List[Player]:
        if names is None:
            names = ["Player 1", "Player 2"]

        assert len(names) == len(set(names)), "Player names must be unique"

        return [cls(name) for name in names]
