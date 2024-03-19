#! /usr/bin/env python

from __future__ import annotations

import copy
from collections import Counter
from typing import Tuple

import attrs

from pooltool.events.datatypes import EventType
from pooltool.events.filter import by_ball, by_time, by_type, filter_events
from pooltool.ruleset.datatypes import (
    BallInHandOptions,
    Ruleset,
    ShotConstraints,
    ShotInfo,
)
from pooltool.ruleset.utils import (
    StateProbe,
    balls_that_hit_cushion,
    get_ball_ids_on_table,
    get_highest_ball,
    get_lowest_ball,
    get_pocketed_ball_ids_during_shot,
    is_ball_hit,
    is_ball_pocketed,
    is_lowest_hit_first,
    is_numbered_ball_pocketed,
    respot,
)
from pooltool.system.datatypes import System


def _is_legal_break(shot: System) -> Tuple[bool, str]:
    if is_ball_pocketed(shot, "cue"):
        return False, "Cue ball in pocket!"

    ball_pocketed = bool(len(get_pocketed_ball_ids_during_shot(shot)))
    enough_cushions = len(balls_that_hit_cushion(shot, exclude={"cue"})) >= 4

    legal = ball_pocketed or enough_cushions
    reason = "" if legal else "4 rails must be contacted, or 1 ball potted"

    return legal, reason


def _is_cushion_hit_after_first_contact(shot: System) -> bool:
    first_contact_event = filter_events(
        shot.events,
        by_ball("cue"),
        by_type(EventType.BALL_BALL),
    )

    if not len(first_contact_event):
        return False

    first_contact_event = first_contact_event[0]

    post_first_contact_cushion_hits = filter_events(
        shot.events,
        by_time(first_contact_event.time),
        by_type([EventType.BALL_LINEAR_CUSHION, EventType.BALL_CIRCULAR_CUSHION]),
    )

    return bool(len(post_first_contact_cushion_hits))


def is_legal(shot: System, break_shot: bool) -> Tuple[bool, str]:
    """Returns whether or not a shot is legal, and the reason"""
    if break_shot:
        return _is_legal_break(shot)

    cushion_after_contact = _is_cushion_hit_after_first_contact(shot)
    ball_pocketed = is_numbered_ball_pocketed(shot)

    reason = ""
    legal = True
    if not is_ball_hit(shot):
        legal = False
        reason = "No ball contacted"
    elif not is_lowest_hit_first(shot):
        legal = False
        reason = "Lowest ball not hit first"
    elif is_ball_pocketed(shot, "cue"):
        legal = False
        reason = "Cue ball in pocket!"
    elif not cushion_after_contact and not ball_pocketed:
        legal = False
        reason = "Cushion not contacted after first contact"

    return (legal, reason)


def is_turn_over(shot: System, legal: bool) -> bool:
    if not legal:
        return True

    ids = get_pocketed_ball_ids_during_shot(shot, exclude={"cue"})

    if len(ids):
        return False

    return True


def is_game_over(shot: System, legal: bool) -> bool:
    if not legal:
        return False

    return get_highest_ball(
        shot, at_start=True
    ).id in get_pocketed_ball_ids_during_shot(shot)


class _NineBall(Ruleset):
    def process_shot(self, shot: System):
        """Override process_shot to add log messages"""
        super().process_shot(shot)

        ball_ids = get_pocketed_ball_ids_during_shot(shot, exclude={"cue"})
        if len(ball_ids):
            sentiment = "neutral" if self.shot_info.turn_over else "good"
            self.log.add_msg(
                f"Ball(s) potted: {', '.join(ball_ids)}", sentiment=sentiment
            )

        if not self.shot_info.legal:
            self.log.add_msg(f"Illegal shot! {self.shot_info.reason}", sentiment="bad")

        if self.shot_info.turn_over:
            self.log.add_msg(f"{self.last_player.name} is up!", sentiment="good")

    def build_shot_info(self, shot: System) -> ShotInfo:
        legal, reason = is_legal(shot, break_shot=self.shot_number == 0)
        turn_over = is_turn_over(shot, legal)
        game_over = is_game_over(shot, legal)
        winner = self.active_player if game_over else None
        score = self.get_score(shot, legal)

        return ShotInfo(
            player=self.active_player,
            legal=legal,
            reason=reason,
            turn_over=turn_over,
            game_over=game_over,
            winner=winner,
            score=score,
        )

    def initial_shot_constraints(self) -> ShotConstraints:
        return ShotConstraints(
            ball_in_hand=BallInHandOptions.BEHIND_LINE,
            movable=["cue"],
            cueable=["cue"],
            hittable=("1",),
            call_shot=False,
        )

    def next_shot_constraints(self, shot: System) -> ShotConstraints:
        return ShotConstraints(
            ball_in_hand=(
                BallInHandOptions.NONE
                if self.shot_info.legal
                else BallInHandOptions.ANYWHERE
            ),
            movable=[] if self.shot_info.legal else ["cue"],
            cueable=["cue"],
            hittable=(get_lowest_ball(shot, when=StateProbe.END).id,),
            call_shot=False,
        )

    def get_score(self, shot: System, legal: bool) -> Counter:
        """APA-style point awards

        This doesn't mean much, because the winner is determined by who sinks the
        9-ball, not who has more points
        """
        if not legal:
            # No points earned for either player on an illegal shot
            return self.score

        points = 0
        for ball_id in get_pocketed_ball_ids_during_shot(shot):
            assert ball_id != "cue", "Legal shot has cue ball in pocket?"
            points += 2 if ball_id == "9" else 1

        points_this_turn = Counter({self.active_player.name: points})
        return self.score + points_this_turn

    def respot_balls(self, shot: System) -> None:
        """Respot balls

        This respots under the following circumstances:

        (1) The shot was illegal, in which case the cue is respotted
        (2) If there are no balls on the table but it was an illegal shot, respot the
            highest ball that was on the table at the start of the shot.
        """
        if not self.shot_info.legal:
            respot(
                shot,
                "cue",
                shot.table.w / 2,
                shot.table.l * 1 / 4,
            )

            ball_ids = get_ball_ids_on_table(shot, at_start=False, exclude={"cue"})
            if not len(ball_ids):
                highest = get_highest_ball(shot, at_start=True)
                respot(
                    shot,
                    highest.id,
                    shot.table.w / 2,
                    shot.table.l * 3 / 4,
                )

    def copy(self) -> _NineBall:
        game = _NineBall()
        game.score = copy.deepcopy(self.score)
        game.shot_number = self.shot_number
        game.turn_number = self.turn_number
        game.shot_constraints = attrs.evolve(self.shot_constraints)
        if hasattr(game, "shot_info"):
            game.shot_info = attrs.evolve(self.shot_info)
        game.players = self.players
        game.active_idx = self.active_idx
        game.log = self.log.copy()
        return game
