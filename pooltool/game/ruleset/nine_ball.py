#! /usr/bin/env python

from collections import Counter
from typing import Optional, Set, Tuple

import attrs

import pooltool.constants as c
from pooltool.events.datatypes import EventType
from pooltool.events.filter import by_ball, by_time, by_type, filter_events
from pooltool.game.ruleset.datatypes import BallInHandOptions, Ruleset, ShotConstraints
from pooltool.game.ruleset.utils import get_id_of_first_ball_hit, get_pocketed_ball_ids
from pooltool.objects.ball.datatypes import Ball
from pooltool.system.datatypes import System


class NineBall(Ruleset):
    def __init__(self, player_names=None):
        Ruleset.__init__(self, player_names=player_names)

    def initial_shot_constraints(self) -> ShotConstraints:
        return ShotConstraints(
            ball_in_hand=BallInHandOptions.BEHIND_LINE,
            movable={"cue"},
            call_shot=False,
        )

    def next_shot_constraints(self, _: System) -> ShotConstraints:
        legal = self.shot_info.is_legal
        return ShotConstraints(
            ball_in_hand=(
                BallInHandOptions.NONE if legal else BallInHandOptions.ANYWHERE
            ),
            movable=set() if legal else {"cue"},
            call_shot=False,
        )

    def get_initial_cueing_ball(self, balls) -> Ball:
        return balls["cue"]

    def award_points(self, shot: System) -> Counter:
        points_for_turn = Counter()

        pocketed_ball_ids = get_pocketed_ball_ids(shot)

        if "cue" in pocketed_ball_ids:
            return points_for_turn

        for ball_id in get_pocketed_ball_ids(shot):
            p = 2 if ball_id == "9" else 1
            points_for_turn[self.active_player.name] += p

        return points_for_turn

    def decide_winner(self, _: System) -> None:
        self.winner = self.active_player

    def respot_balls(self, shot: System) -> None:
        if not self.shot_info.is_legal:
            self.respot(
                shot,
                "cue",
                shot.table.w / 2,
                shot.table.l * 1 / 4,
                shot.balls["cue"].params.R,
            )

        highest = self.get_highest_ball(shot)
        highest_id = highest.id
        lowest_id = self.get_lowest_ball(shot).id

        pocketed_ball_ids = get_pocketed_ball_ids(shot)

        if (
            (highest_id == lowest_id)
            and (highest_id in pocketed_ball_ids)
            and not self.shot_info.is_legal
        ):
            self.respot(
                shot,
                highest_id,
                shot.table.w / 2,
                shot.table.l * 3 / 4,
                highest.params.R,
            )

    def is_turn_over(self, shot: System) -> bool:
        legal, _ = self.legality(shot)
        if not legal:
            return True

        if len(ids := get_pocketed_ball_ids(shot)):
            self.log.add_msg(f"Ball(s) potted: {','.join(ids)}", sentiment="good")
            return False

        return True

    def is_game_over(self, shot: System) -> bool:
        highest_id = self.get_highest_ball(shot).id

        pocketed_ball_ids = get_pocketed_ball_ids(shot)

        if highest_id in pocketed_ball_ids and self.shot_info.is_legal:
            return True
        else:
            return False

    def get_lowest_ball(self, shot: System) -> Ball:
        lowest = Ball.dummy(id="10")

        for ball in shot.balls.values():
            if ball.id == "cue":
                continue
            if ball.history[0].s == c.pocketed:
                continue
            if int(ball.id) < int(lowest.id):
                lowest = ball

        return lowest

    def get_highest_ball(self, shot: System) -> Ball:
        highest = Ball.dummy(id="0")

        for ball in shot.balls.values():
            if ball.id == "cue":
                continue
            if ball.history[0].s == c.pocketed:
                continue
            if int(ball.id) > int(highest.id):
                highest = ball

        return highest

    def is_lowest_hit_first(self, shot: System) -> bool:
        if (ball_id := get_id_of_first_ball_hit(shot, "cue")) is None:
            return False

        return self.get_lowest_ball(shot).id == ball_id

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
        if not self.is_lowest_hit_first(shot):
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

    def legality(self, shot: System) -> Tuple[bool, str]:
        """Returns whether or not a shot is legal, and the reason"""
        reason = ""

        if not self.is_lowest_hit_first(shot):
            reason = "Lowest ball not hit first"
        elif self.is_cue_pocketed(shot):
            reason = "Cue ball in pocket!"
        elif not self.is_cushion_hit_after_first_contact(shot):
            reason = "Cushion not contacted after first contact"
        elif not self.is_legal_break(shot):
            reason = "Must contact 4 rails or pot 1 ball"

        return (True, reason) if not reason else (False, reason)
