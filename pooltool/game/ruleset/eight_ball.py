#! /usr/bin/env python

from typing import Counter, Dict, Optional, Set, Tuple

import pooltool.constants as c
from pooltool.events.datatypes import EventType
from pooltool.events.filter import by_ball, by_time, by_type, filter_events, filter_type
from pooltool.game.ruleset.datatypes import BallInHandOptions, Ruleset, ShotConstraints
from pooltool.game.ruleset.utils import (
    get_id_of_first_ball_hit,
    get_pocketed_ball_ids,
    is_ball_pocketed,
)
from pooltool.objects.ball.datatypes import Ball
from pooltool.system.datatypes import System
from pooltool.utils.strenum import StrEnum, auto


class Target(StrEnum):
    SOLIDS = auto()
    STRIPES = auto()
    EIGHT = auto()
    UNDECIDED = auto()


target_dict: Dict[str, Set[str]] = {
    Target.SOLIDS: {str(i) for i in range(1, 8)},
    Target.STRIPES: {str(i) for i in range(9, 16)},
    Target.UNDECIDED: {str(i) for i in range(1, 16) if i != 8},
    Target.EIGHT: {"8"},
}


class EightBall(Ruleset):
    def __init__(self):
        Ruleset.__init__(self, True, True, None)

        self.solids = [str(i) for i in range(1, 8)]
        self.stripes = [str(i) for i in range(9, 16)]

        # Solids or stripes undetermined
        self.targeting: Dict[str, Target] = {}
        for player in self.players:
            self.targeting[player.name] = Target.UNDECIDED

        for player in self.players:
            player.target_balls = []

    @property
    def active_balls(self) -> Set[str]:
        """Return the list of ball IDs associated with active player's target"""
        return target_dict[self.active_target]

    @property
    def active_target(self) -> Target:
        """Return the active player's Target (SOLIDS, STRIPES, UNDECIDED, EIGHT)"""
        return self.targeting[self.active_player.name]

    def start(self, _: System) -> None:
        self.active_player.ball_in_hand = "cue"

        # These are the initial shot constraints. On the break one doesn't have to call
        # the ball, or the pocket, and the cue remains behind the line.
        self.shot_constraints = ShotConstraints(
            ball_in_hand=BallInHandOptions.BEHIND_LINE,
            call_ball=False,
            call_pocket=False,
        )

    def get_initial_cueing_ball(self, balls) -> Ball:
        return balls["cue"]

    def award_points(self, shot: System) -> Counter:
        legal, _ = self.legality(shot)
        if not legal:
            return Counter()

        # At this point the shot was legal, so no cue ball was sunk and no 8-ball was
        # sunk out of turn. Therefore we can return the number of potted balls

        return Counter({self.active_player.name: len(get_pocketed_ball_ids(shot))})

    def decide_winner(self, _: System):
        if self.shot_info.is_legal:
            self.winner = self.active_player
            return

        self.winner = (
            self.players[0]
            if self.players[0] != self.active_player
            else self.players[1]
        )

    def award_ball_in_hand(self, shot: System, legal: bool) -> Optional[str]:
        if not legal:
            self.respot(
                shot,
                "cue",
                shot.table.w / 2,
                shot.table.l * 1 / 4,
                shot.balls["cue"].params.R,
            )
            return "cue"
        else:
            return None

    def respot_balls(self, _: System):
        """No balls respotted in this variant of 8-ball"""

    def is_turn_over(self, shot: System) -> bool:
        legal, _ = self.legality(shot)
        if not legal:
            return True

        pocket_events = filter_type(shot.events, EventType.BALL_POCKET)

        if self.active_target == Target.UNDECIDED and len(pocket_events):
            return False

        for event in pocket_events:
            ball_id, pocket_id = event.ids
            if ball_id == self.ball_call and pocket_id == self.pocket_call:
                self.log.add_msg(f"Ball potted: {ball_id}", sentiment="good")
                return False

        return True

    def is_game_over(self, shot: System) -> bool:
        return is_ball_pocketed(shot, "8")

    def is_object_ball_hit_first(self, shot: System) -> bool:
        ball_id = get_id_of_first_ball_hit(shot, "cue")

        if not ball_id:
            return False

        if self.active_target == Target.UNDECIDED:
            # stripes or solids not yet determined, so every ball is target ball
            return True

        return ball_id == self.ball_call

    def is_legal_break(self, shot: System) -> bool:
        if self.shot_number != 0:
            return True

        ball_pocketed = bool(len(get_pocketed_ball_ids(shot)))
        enough_cushions = len(self.numbered_balls_that_hit_cushion(shot)) >= 4

        return ball_pocketed or enough_cushions

    def numbered_balls_that_hit_cushion(self, shot: System) -> Set[str]:
        numbered_ball_ids = [
            ball.id for ball in shot.balls.values() if ball.id != "cue"
        ]

        cushion_events = filter_events(
            shot.events,
            by_type([EventType.BALL_LINEAR_CUSHION, EventType.BALL_CIRCULAR_CUSHION]),
            by_ball(numbered_ball_ids),
        )

        return set(event.agents[0].id for event in cushion_events)

    def is_cue_pocketed(self, shot: System) -> bool:
        return "cue" in get_pocketed_ball_ids(shot)

    def is_cushion_hit_after_first_contact(self, shot: System) -> bool:
        if not self.is_object_ball_hit_first(shot):
            return False

        numbered_balls_pocketed = filter_events(
            shot.events,
            by_type(EventType.BALL_POCKET),
            by_ball([ball.id for ball in shot.balls.values() if ball.id != "cue"]),
        )

        first_contact_event = filter_events(
            shot.events,
            by_ball("cue"),
            by_type(EventType.BALL_BALL),
        )[0]

        post_first_contact_cushion_hits = filter_events(
            shot.events,
            by_time(first_contact_event.time),
            by_ball("cue"),
            by_type([EventType.BALL_LINEAR_CUSHION, EventType.BALL_CIRCULAR_CUSHION]),
        )

        ball_was_pocketed = bool(len(numbered_balls_pocketed))
        cushion_hit_after_first_contact = bool(len(post_first_contact_cushion_hits))

        return ball_was_pocketed or cushion_hit_after_first_contact

    def is_8_ball_pocketed_out_of_turn(self, shot: System) -> bool:
        if "8" in self.active_balls:
            # Player is on the 8-ball, so it can't be out of turn
            return False

        # If it was pocketed, it was pocketed out of turn
        return is_ball_pocketed(shot, "8")

    def legality(self, shot) -> Tuple[bool, str]:
        """Returns whether or not a shot is legal, and the reason"""
        reason = ""

        if self.is_8_ball_pocketed_out_of_turn(shot):
            reason = "8-ball sunk before others!"
        elif not self.is_object_ball_hit_first(shot):
            reason = "Object ball not hit first"
        elif not self.is_shot_called(shot):
            reason = "No shot called!"
        elif self.is_cue_pocketed(shot):
            reason = "Cue ball in pocket!"
        elif not self.is_cushion_hit_after_first_contact(shot):
            reason = "Cushion not contacted after first contact"
        elif not self.is_legal_break(shot):
            reason = "Must contact 4 rails or pot 1 ball"

        return (True, reason) if not reason else (False, reason)

    def is_shot_called(self, _: System) -> bool:
        if self.shot_number == 0:
            return True

        if self.ball_call is None or self.pocket_call is None:
            return False

        return True

    def advance(self, shot: System):
        self.on_8_ball(shot)
        self.decide_stripes_or_solids(shot)
        super().advance(shot)

    def on_8_ball(self, shot: System):
        for player in self.players:
            states = [
                ball.state.s
                for ball in shot.balls.values()
                if ball.id in target_dict[self.targeting[player.name]]
            ]
            if all([state == c.pocketed for state in states]):
                self.targeting[player.name] = Target.EIGHT

    def decide_stripes_or_solids(self, shot: System):
        if self.active_target != Target.UNDECIDED:
            # Stripes/solids has already been determined
            return

        if self.shot_info.is_turn_over:
            # Player didn't sink a ball
            return

        if self.ball_call in target_dict[Target.STRIPES]:
            self.targeting[self.active_player.name] = Target.STRIPES
            self.targeting[self.last_player.name] = Target.SOLIDS
        elif self.ball_call in target_dict[Target.SOLIDS]:
            self.targeting[self.active_player.name] = Target.SOLIDS
            self.targeting[self.last_player.name] = Target.STRIPES
        else:
            raise NotImplementedError("This should not happen")

        self.log.add_msg(
            f"{self.active_player.name} takes {self.active_target}",
            sentiment="good",
        )

    def next_shot_constraints(self, _: System) -> ShotConstraints:
        return ShotConstraints(
            ball_in_hand=(
                BallInHandOptions.NONE
                if self.shot_info.is_legal
                else BallInHandOptions.ANYWHERE
            ),
            call_ball=True,
            call_pocket=True,
        )
