#! /usr/bin/env python

from typing import Counter, Dict, List, Optional, Set, Tuple

import pooltool.constants as c
from pooltool.events.datatypes import EventType
from pooltool.events.filter import by_ball, by_time, by_type, filter_events, filter_type
from pooltool.game.ruleset.datatypes import Ruleset
from pooltool.game.ruleset.utils import get_id_of_first_ball_hit, get_pocketed_ball_ids
from pooltool.objects.ball.datatypes import Ball
from pooltool.system.datatypes import System
from pooltool.utils.strenum import StrEnum, auto


class TargetBalls(StrEnum):
    SOLIDS = auto()
    STRIPES = auto()
    EIGHT = auto()
    UNDECIDED = auto()


target_balls_dict: Dict[str, List[str]] = {
    TargetBalls.SOLIDS: [str(i) for i in range(1, 8)],
    TargetBalls.STRIPES: [str(i) for i in range(9, 16)],
    TargetBalls.EIGHT: ["8"],
    TargetBalls.UNDECIDED: [],
}


class EightBall(Ruleset):
    def __init__(self):
        Ruleset.__init__(self, True, True, None)

        self.solids = [str(i) for i in range(1, 8)]
        self.stripes = [str(i) for i in range(9, 16)]

        # Solids or stripes undetermined
        self.targeting: Dict[str, TargetBalls] = {}
        for player in self.players:
            self.targeting[player.name] = TargetBalls.UNDECIDED

        for player in self.players:
            player.target_balls = []

    def target_balls(self) -> List[str]:
        return target_balls_dict[self.active_player_targeting()]

    def active_player_targeting(self) -> TargetBalls:
        return self.targeting[self.active_player.name]

    def start(self, _: System) -> None:
        self.active_player.ball_in_hand = "cue"

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

        if self.active_player_targeting() == TargetBalls.UNDECIDED and len(
            pocket_events
        ):
            return False

        for event in pocket_events:
            ball_id, pocket_id = event.ids
            if ball_id == self.ball_call and pocket_id == self.pocket_call:
                self.log.add_msg(f"Ball potted: {ball_id}", sentiment="good")
                return False

        return True

    def is_game_over(self, shot: System) -> bool:
        return any(
            "8" in event.agents[0].id
            for event in filter_type(shot.events, EventType.BALL_POCKET)
        )

    def is_object_ball_hit_first(self, shot: System) -> bool:
        ball_id = get_id_of_first_ball_hit(shot, "cue")

        ball_was_hit = ball_id is not None
        if not ball_was_hit:
            return True

        if self.active_player_targeting() == TargetBalls.UNDECIDED:
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

    def is_8_ball_sunk_before_others(self, shot: System) -> bool:
        if "8" in self.target_balls():
            # Player is on the 8-ball, so it's not out of turn
            return False

        return any(
            "8" in event.agents[0].id
            for event in filter_type(shot.events, EventType.BALL_POCKET)
        )

    def legality(self, shot) -> Tuple[bool, str]:
        """Returns whether or not a shot is legal, and the reason"""
        reason = ""

        if self.is_8_ball_sunk_before_others(shot):
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

    def advance(self, shot):
        self.update_target_balls(shot)
        self.decide_stripes_or_solids(shot)
        super().advance(shot)

    def update_target_balls(self, shot: System):
        for player in self.players:
            if self.shot_number == 0:
                player.target_balls = self.solids + self.stripes

            states = [
                ball.state.s
                for ball in shot.balls.values()
                if ball.id in player.target_balls
            ]
            if all([state == c.pocketed for state in states]):
                player.target_balls.append("8")

    def decide_stripes_or_solids(self, shot):
        is_open = True if self.target_balls() is None else False
        player_potted = not self.shot_info["is_turn_over"]
        is_break_shot = self.shot_number == 0

        if (not is_open) or (not player_potted) or (is_break_shot):
            return

        if self.ball_call.id in self.stripes:
            self.target_balls() == "stripes"
            self.active_player.target_balls = self.stripes
            other_player = (
                self.players[0]
                if self.players[0] != self.active_player
                else self.players[1]
            )
            other_player.stripes_or_solids = "solids"
            other_player.target_balls = self.solids
        else:
            self.target_balls() == "solids"
            self.active_player.target_balls = self.solids
            other_player = (
                self.players[0]
                if self.players[0] != self.active_player
                else self.players[1]
            )
            other_player.stripes_or_solids = "stripes"
            other_player.target_balls = self.stripes

        self.log.add_msg(
            f"{self.active_player.name} takes {self.target_balls()}",
            sentiment="good",
        )
