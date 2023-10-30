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


class Log:
    def __init__(self):
        self.timer = Timer()
        self.msgs = []

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


class Ruleset(ABC):
    def __init__(
        self,
        is_call_pocket: bool,
        is_call_ball: bool,
        player_names: Optional[List[str]] = None,
    ) -> None:
        self.is_call_ball = is_call_ball
        self.is_call_pocket = is_call_pocket

        self.points: Counter = Counter()
        self.tie: bool = False
        self.game_over = False
        self.shot_number: int = 0
        self.turn_number: int = 0
        self.ball_in_hand: Optional[str] = None
        self.ball_call: str = "dummy"
        self.pocket_call: str = "dummy"
        self.active_player: Player = Player.dummy()
        self.log: Log = Log()

        self.shot_info: ShotInfo
        self.winner: Player

        self.players: List[Player] = Player.create_players(player_names)
        self.set_next_player()

    def player_order(self) -> Generator[Player, None, None]:
        for i in range(len(self.players)):
            yield self.players[(self.turn_number + i) % len(self.players)]

    def set_next_player(self):
        next_player = self.players[self.turn_number % len(self.players)]
        if next_player != self.active_player:
            self.last_player, self.active_player = self.active_player, next_player
            self.active_player.is_shooting = True
            if self.last_player:
                self.last_player.is_shooting = False

            self.log.add_msg(f"{self.active_player.name} is up", sentiment="neutral")

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

    def advance(self, shot):
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

        self.ball_call = Ball.dummy()
        self.pocket_call = Pocket.dummy()

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
    def start(self, shot: Optional[System] = None):
        pass


def _get_id() -> str:
    return uuid.uuid4().hex


@attrs.define
class Player:
    name: str
    is_shooting: bool = attrs.field(default=False)
    target_balls: List[str] = attrs.field(factory=list)
    ball_in_hand: Optional[str] = attrs.field(default=None)

    id: str = attrs.field(factory=_get_id, init=False)

    @classmethod
    def create_players(cls, names: Optional[List[str]] = None) -> List[Player]:
        if names is None:
            names = ["Player 1", "Player 2"]

        return [cls(name) for name in names]

    @classmethod
    def dummy(cls) -> Player:
        return cls(name="dummy")
