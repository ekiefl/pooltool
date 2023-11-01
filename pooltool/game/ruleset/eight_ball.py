#! /usr/bin/env python

from typing import Counter, Dict, List, Set, Tuple

import pooltool.constants as c
from pooltool.events.datatypes import EventType
from pooltool.events.filter import by_ball, by_time, by_type, filter_events, filter_type
from pooltool.game.ruleset.datatypes import BallInHandOptions, Ruleset, ShotConstraints
from pooltool.game.ruleset.utils import (
    get_id_of_first_ball_hit,
    get_pocketed_ball_ids,
    is_ball_pocketed,
)
from pooltool.system.datatypes import System
from pooltool.utils.strenum import StrEnum, auto


class Target(StrEnum):
    SOLIDS = auto()
    STRIPES = auto()
    EIGHT = auto()
    UNDECIDED = auto()


target_dict: Dict[str, List[str]] = {
    Target.SOLIDS: [str(i) for i in range(1, 8)],
    Target.STRIPES: [str(i) for i in range(9, 16)],
    Target.UNDECIDED: [str(i) for i in range(1, 16) if i != 8],
    Target.EIGHT: ["8"],
}


class EightBall(Ruleset):
    def __init__(self, player_names=None):
        Ruleset.__init__(self, player_names=player_names)

        # Solids or stripes undetermined
        self.targeting: Dict[str, Target] = {}
        for player in self.players:
            self.targeting[player.name] = Target.UNDECIDED

    def initial_shot_constraints(self) -> ShotConstraints:
        return ShotConstraints(
            ball_in_hand=BallInHandOptions.BEHIND_LINE,
            movable=["cue"],
            cueable=["cue"],
            hittable=target_dict[Target.UNDECIDED],
            call_shot=False,
        )

    def next_shot_constraints(self, shot: System) -> ShotConstraints:
        if self.legality(shot)[0]:
            ball_in_hand = BallInHandOptions.NONE
            movable = []
        else:
            ball_in_hand = BallInHandOptions.ANYWHERE
            movable = ["cue"]

        if self.is_turn_over(shot):
            hittable = target_dict[self.next_target]
        else:
            hittable = target_dict[self.active_target]

        return ShotConstraints(
            ball_in_hand=ball_in_hand,
            movable=movable,
            cueable=["cue"],
            hittable=hittable,
            call_shot=True,
        )

    @property
    def active_target(self) -> Target:
        """Return the active player's Target (SOLIDS, STRIPES, UNDECIDED, EIGHT)"""
        return self.targeting[self.active_player.name]

    @property
    def next_target(self) -> Target:
        """Return the next player's Target (SOLIDS, STRIPES, UNDECIDED, EIGHT)

        Note: The next player is the same as the last player since it's a two player game
        """
        return self.targeting[self.last_player.name]

    def award_points(self, shot: System) -> Counter:
        """FIXME

        Currently some inaccuracies resulting from balls being potted before
        stripes/solids is determined. Until a functional approach replaces the poor base
        class design, we are stuck with this structural constraint.
        """
        legal, _ = self.legality(shot)
        if not legal:
            return Counter()

        return Counter({self.active_player.name: len(get_pocketed_ball_ids(shot))})

    def decide_winner(self, shot: System):
        if self.legality(shot)[0]:
            self.winner = self.active_player
            return

        self.winner = (
            self.players[0]
            if self.players[0] != self.active_player
            else self.players[1]
        )

    def respot_balls(self, shot: System):
        """No balls respotted in this variant of 8-ball"""
        if not self.legality(shot)[0]:
            self.respot(
                shot,
                "cue",
                shot.table.w / 2,
                shot.table.l * 1 / 4,
                shot.balls["cue"].params.R,
            )

    def is_turn_over(self, shot: System) -> bool:
        legal, _ = self.legality(shot)
        if not legal:
            return True

        pocket_events = filter_type(shot.events, EventType.BALL_POCKET)

        if self.active_target == Target.UNDECIDED and len(pocket_events) > 0:
            return False

        called_ball_pocketed = False
        called_ball_in_wrong_pocket = False

        for event in pocket_events:
            ball_id, pocket_id = event.ids
            if ball_id == self.shot_constraints.ball_call:
                if pocket_id == self.shot_constraints.pocket_call:
                    called_ball_pocketed = True
                    break
                else:
                    called_ball_in_wrong_pocket = True

        if called_ball_pocketed:
            pocketed_balls = get_pocketed_ball_ids(shot)
            self.log.add_msg(
                f"Nice! Ball(s) potted: {pocketed_balls}", sentiment="good"
            )
            return False

        if called_ball_in_wrong_pocket:
            self.log.add_msg(
                f"{self.shot_constraints.ball_call} ball potted in wrong pocket!",
                sentiment="neutral",
            )

        return True

    def is_game_over(self, shot: System) -> bool:
        return is_ball_pocketed(shot, "8")

    def is_target_group_hit_first(self, shot: System) -> bool:
        ball_id = get_id_of_first_ball_hit(shot, "cue")

        if ball_id is None:
            return False

        return ball_id in target_dict[self.active_target]

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
        if not self.is_target_group_hit_first(shot):
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
            by_type([EventType.BALL_LINEAR_CUSHION, EventType.BALL_CIRCULAR_CUSHION]),
        )

        ball_was_pocketed = bool(len(numbered_balls_pocketed))
        cushion_hit_after_first_contact = bool(len(post_first_contact_cushion_hits))

        return ball_was_pocketed or cushion_hit_after_first_contact

    def is_8_ball_pocketed_out_of_turn(self, shot: System) -> bool:
        if self.active_target == Target.UNDECIDED:
            # Player is on the 8-ball, so it can't be out of turn
            return False

        # If it was pocketed, it was pocketed out of turn
        return is_ball_pocketed(shot, "8")

    def legality(self, shot) -> Tuple[bool, str]:
        """Returns whether or not a shot is legal, and the reason"""
        reason = ""

        if self.is_8_ball_pocketed_out_of_turn(shot):
            reason = "8-ball sunk before others!"
        elif not self.is_target_group_hit_first(shot):
            reason = f"Incorrect ball hit first"
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
        if not self.shot_constraints.call_shot:
            return True

        if (
            self.shot_constraints.ball_call is None
            or self.shot_constraints.pocket_call is None
        ):
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

        if self.is_turn_over(shot):
            # Player didn't sink a ball
            return

        if not self.shot_constraints.call_shot:
            # It's the break shot, no call shot is required
            return

        if self.shot_constraints.ball_call not in get_pocketed_ball_ids(shot):
            return

        if self.shot_constraints.ball_call in target_dict[Target.STRIPES]:
            self.targeting[self.active_player.name] = Target.STRIPES
            self.targeting[self.last_player.name] = Target.SOLIDS
        elif self.shot_constraints.ball_call in target_dict[Target.SOLIDS]:
            self.targeting[self.active_player.name] = Target.SOLIDS
            self.targeting[self.last_player.name] = Target.STRIPES
        else:
            raise NotImplementedError("This should not happen")

        self.log.add_msg(
            f"{self.active_player.name} takes {self.active_target}",
            sentiment="good",
        )
