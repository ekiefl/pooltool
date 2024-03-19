#! /usr/bin/env python
from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from typing import (
    Any,
    Callable,
    Counter,
    Dict,
    Generator,
    List,
    Optional,
    Protocol,
    Tuple,
)

import attrs

from pooltool.ai.action import Action
from pooltool.system.datatypes import System
from pooltool.terminal import Timer
from pooltool.utils.strenum import StrEnum, auto


class AIPlayer(Protocol):
    def decide(
        self,
        system: System,
        game: Ruleset,
        callback: Optional[Callable[[Action], None]] = None,
    ) -> Action: ...

    def apply(self, system: System, action: Action) -> None: ...


@attrs.define
class Player:
    """A player

    Attributes:
        name:
            Player's name.
        ai:
            Not implemented yet...
    """

    name: str
    ai: Optional[AIPlayer] = None

    @property
    def is_ai(self) -> bool:
        return self.ai is not None


@attrs.define
class Log:
    msgs: List[Dict[str, Any]] = attrs.field(factory=list)
    timer: Timer = attrs.field(factory=Timer.factory)
    update: bool = attrs.field(default=False)

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

    def copy(self) -> Log:
        return attrs.evolve(
            self,
            timer=copy.deepcopy(self.timer),
            msgs=copy.deepcopy(self.msgs),
        )


class BallInHandOptions(StrEnum):
    NONE = auto()
    ANYWHERE = auto()
    BEHIND_LINE = auto()
    SEMICIRCLE = auto()


@attrs.define
class ShotConstraints:
    """Constraints for a player's upcoming shot

    Attributes:
        ball_in_hand:
            Enum specifying if and how the player can place the cue ball by hand.
        movable:
            A list of identifiers for balls that the player is allowed to move
            before the shot. If None, all balls are considered movable.
        cueable:
            A list of identifiers for balls that can be struck by the cue ball
            during the shot. If None, all balls are considered cueable.
        hittable:
            A tuple of identifiers for balls that must be hit for the shot to be
            considered legal.
        call_shot:
            A boolean indicating whether the shot must be called (i.e., the player must
            declare which ball they intend to pocket and in which pocket). If False,
            ball_call and pocket_call need not be defined.
        ball_call:
            The identifier of the ball the player has called to be pocketed.
            If None, no specific ball has been called.
        pocket_call:
            The identifier of the pocket the player has called for the ball to
            be pocketed in. If None, no specific pocket has been called.
    """

    ball_in_hand: BallInHandOptions
    movable: Optional[List[str]]
    cueable: Optional[List[str]]
    hittable: Tuple[str, ...]
    call_shot: bool
    ball_call: Optional[str] = attrs.field(default=None)
    pocket_call: Optional[str] = attrs.field(default=None)

    def cueball(self, balls: Dict[str, Any]) -> str:
        if self.cueable is None:
            assert len(balls)

            for cue in ("cue", "white", "yellow"):
                if cue in balls:
                    return cue

            return list(balls.keys())[0]

        return self.cueable[0]

    def can_shoot(self) -> bool:
        if (
            self.call_shot
            and self.ball_call is not None
            and self.pocket_call is not None
        ):
            return True
        elif not self.call_shot:
            return True
        else:
            return False


@attrs.define(frozen=True)
class ShotInfo:
    """Info about a played shot

    Attributes:
        player:
            The player who played the shot.
        legal:
            Whether or not the shot was legal.
        reason:
            A textual description providing the rationale for whether the shot was
            legal.
        turn_over:
            Whether the player's turn is over.
        game_over:
            Whether or not the game is over as a result of the shot.
        winner:
            Who the winner is. None if :attr:`game_over` is False.
        score:
            The total game score (tallied after the shot). Keys are player names and
            values are points.
    """

    player: Player
    legal: bool
    reason: str
    turn_over: bool
    game_over: bool
    winner: Optional[Player]
    score: Counter[str]


class Ruleset(ABC):
    """Abstract base class for a pool game ruleset.

    This class defines the skeleton of a pool game ruleset, including player management,
    score tracking, and shot handling. Subclasses must implement the abstract methods to
    specify the behavior for specific games. For examples, see currently implemented
    games.
    """

    def __init__(self, players: Optional[List[Player]] = None) -> None:
        # Player info
        players = [] if players is None else players
        self.players: List[Player] = players
        self.active_idx: int = 0

        # Game progress tracking
        self.score: Counter[str] = Counter()
        self.shot_number: int = 0
        self.turn_number: int = 0

        # Game states
        self.shot_constraints: ShotConstraints = self.initial_shot_constraints()
        self.shot_info: ShotInfo

        self.log: Log = Log()

    @property
    def active_player(self) -> Player:
        return self.players[self.active_idx]

    @property
    def last_player(self) -> Player:
        """Returns the last player who played before the active player

        If no turns have occurred, meaning the active player is the first player to
        shoot in the game, this erroneously returns the last player in the player order.
        """
        last_idx = (self.active_idx - 1) % len(self.players)
        return self.players[last_idx]

    def set_next_player(self) -> None:
        """Sets the index for the next player

        It is through this index that self.last_player and self.active_player are
        defined from.
        """
        self.active_idx = self.turn_number % len(self.players)

    def player_order(self) -> Generator[Player, None, None]:
        """Generates player order from current player until last-to-play"""
        for i in range(len(self.players)):
            yield self.players[(self.turn_number + i) % len(self.players)]

    def process_shot(self, shot: System) -> None:
        """Processes the information of the shot just played

        Args:
            shot: The shot data from the system.
        """
        self.shot_info = self.build_shot_info(shot)
        self.score = self.shot_info.score
        self.respot_balls(shot)

    def advance(self, shot: System) -> None:
        """Advances the game state after a shot has been made and processed

        Args:
            shot: The shot data from the system.
        """
        if self.shot_info.game_over:
            if (winner := self.shot_info.winner) is not None:
                self.log.add_msg(f"Game over! {winner.name} wins!", sentiment="good")
            else:
                self.log.add_msg("Game over! Tie game!", sentiment="good")
            return

        if self.shot_info.turn_over:
            self.turn_number += 1
        self.shot_number += 1

        self.shot_constraints = self.next_shot_constraints(shot)
        shot.cue.cue_ball_id = self.shot_constraints.cueball(shot.balls)
        self.set_next_player()

    def process_and_advance(self, shot: System) -> None:
        self.process_shot(shot)
        self.advance(shot)

    @abstractmethod
    def build_shot_info(self, shot: System) -> ShotInfo:
        """Construct the ShotInfo object for the current shot

        This method evaluates the legality of a shot, determines if the turn or game is
        over, and if applicable, decides the winner.

        Args:
            shot: The current shot being played.

        Returns:
            ShotInfo:
                Contains details about the legality of the shot, whether the turn and
                game are over, and who the winner is, if there is one.
        """

    @abstractmethod
    def next_shot_constraints(self, shot: System) -> ShotConstraints:
        """Determine the constraints for the next shot based on the current game state.

        The method sets the conditions under which the next shot will be played, such as
        whether ball-in-hand rules apply and which balls are legally hittable.

        Args:
            shot: The current shot being played.

        Returns:
            ShotConstraints:
                Shot constraints for the next shot.
        """

    @abstractmethod
    def initial_shot_constraints(self) -> ShotConstraints:
        """Define the initial constraints for the first shot of the game.

        Returns:
            ShotConstraints:
                Predefined shot constraints for the initial shot.
        """

    @abstractmethod
    def respot_balls(self, shot: System) -> None:
        """Respot balls

        This method should decide which balls should be respotted, and respot them. This
        method should probably make use of ``pooltool.ruleset.utils.respot``
        """

    @abstractmethod
    def copy(self) -> Ruleset:
        """Copy the game state

        If you don't know how to implement this method, you can create a placeholder
        function:

        ::
            def copy(self):
                return self
        """
        pass
