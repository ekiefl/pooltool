#! /usr/bin/env python

from __future__ import annotations

from typing import Counter

from pooltool.events.datatypes import Event, EventType
from pooltool.events.filter import by_ball, by_time, by_type, filter_events
from pooltool.ruleset.datatypes import (
    BallInHandOptions,
    Player,
    Ruleset,
    ShotConstraints,
    ShotInfo,
)
from pooltool.system.datatypes import System


def _other(cue: str, event: Event) -> str:
    for id in event.ids:
        if id != cue:
            return id

    raise Exception()


def is_turn_over(shot: System, constraints: ShotConstraints) -> bool:
    assert constraints.cueable is not None
    cue = constraints.cueable[0]

    # Find when the second ball is first hit by the cue-ball

    ball_hits = filter_events(
        shot.events,
        by_type(EventType.BALL_BALL),
        by_ball(cue),
    )

    hits = set()
    for event in ball_hits:
        hits.add(_other(cue, event))
        if len(hits) == 2:
            break
    else:
        return True

    # Now calculate all cue-ball cushion hits before that event

    cushion_hits = filter_events(
        shot.events,
        by_type(EventType.BALL_LINEAR_CUSHION),
        by_ball(cue),
        by_time(event.time, after=False),
    )

    return len(cushion_hits) < 3


def is_game_over(
    score: Counter, active: Player, turn_over: bool, win_condition: int
) -> bool:
    if turn_over:
        return False

    return score[active.name] == win_condition


def next_cue(current_cue: str, num_players: int) -> str:
    assert current_cue in ("white", "yellow", "red")
    assert num_players in (2, 3)

    if num_players == 3:
        return {"white": "yellow", "yellow": "red", "red": "white"}[current_cue]

    return "white" if current_cue == "yellow" else "yellow"


class _ThreeCushion(Ruleset):
    def __init__(self, *args, win_condition: int = 10, **kwargs):
        self.win_condition = win_condition
        Ruleset.__init__(self, *args, **kwargs)

    def build_shot_info(self, shot: System) -> ShotInfo:
        turn_over = is_turn_over(shot, self.shot_constraints)
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
            cueable=["white"],
            hittable=tuple(),
            call_shot=False,
        )

    def next_shot_constraints(self, shot: System) -> ShotConstraints:
        assert (cueable := self.shot_constraints.cueable) is not None

        if self.shot_info.turn_over:
            cueable = [next_cue(cueable[0], len(self.players))]

        return ShotConstraints(
            ball_in_hand=BallInHandOptions.NONE,
            movable=[],
            cueable=cueable,
            hittable=tuple(),
            call_shot=False,
        )

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

    def copy(self) -> _ThreeCushion:
        raise NotImplementedError("ThreeCushion copy needs to be implemented")
