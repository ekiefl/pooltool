#! /usr/bin/env python

from __future__ import annotations

from typing import Counter

from pooltool.events.datatypes import EventType
from pooltool.events.filter import by_ball, by_type, filter_events, filter_type
from pooltool.ruleset.datatypes import (
    BallInHandOptions,
    Player,
    Ruleset,
    ShotConstraints,
    ShotInfo,
)
from pooltool.system.datatypes import System


def is_turn_over(shot: System) -> bool:
    # See whether cue contacted object ball
    ball_hits = filter_type(shot.events, EventType.BALL_BALL)
    if not len(ball_hits):
        return True

    # Count rails that cue ball hits
    cue_cushion_hits = filter_events(
        shot.events,
        by_type(EventType.BALL_LINEAR_CUSHION),
        by_ball("cue"),
    )

    # Count rails that object ball hits
    object_cushion_hits = filter_events(
        shot.events,
        by_type(EventType.BALL_LINEAR_CUSHION),
        by_ball("object"),
    )

    return len(cue_cushion_hits) + len(object_cushion_hits) != 3


def is_game_over(
    score: Counter, active: Player, turn_over: bool, win_condition: int
) -> bool:
    if turn_over:
        return False

    return score[active.name] == win_condition


class _SumToThree(Ruleset):
    def __init__(self, *args, win_condition: int = 10, **kwargs):
        self.win_condition = win_condition
        Ruleset.__init__(self, *args, **kwargs)

    def build_shot_info(self, shot: System) -> ShotInfo:
        turn_over = is_turn_over(shot)
        score = self.get_score(self.score, turn_over)
        game_over = is_game_over(
            score,
            self.active_player,
            turn_over,
            self.win_condition,
        )

        return ShotInfo(
            player=self.active_player,
            legal=True,
            reason="",
            turn_over=turn_over,
            game_over=game_over,
            winner=self.active_player if game_over else None,
            score=score,
        )

    def initial_shot_constraints(self) -> ShotConstraints:
        return ShotConstraints(
            ball_in_hand=BallInHandOptions.NONE,
            movable=[],
            cueable=["cue"],
            hittable=("object",),
            call_shot=False,
        )

    def next_shot_constraints(self, shot: System) -> ShotConstraints:
        return self.shot_constraints

    def get_score(self, score: Counter, turn_over: bool) -> Counter:
        if turn_over:
            return score

        score[self.active_player.name] += 1
        return score

    def respot_balls(self, shot: System) -> None:
        pass

    def process_shot(self, shot: System):
        """Override process_shot to add log messages"""
        super().process_shot(shot)

        if self.shot_info.turn_over:
            self.log.add_msg(f"{self.last_player.name} is up!", sentiment="good")

    def copy(self) -> _SumToThree:
        raise NotImplementedError("ThreeCushion copy needs to be implemented")
