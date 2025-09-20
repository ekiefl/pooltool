#! /usr/bin/env python

from __future__ import annotations

from collections import Counter

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


def is_point(shot: System) -> bool:
    cue_id = shot.cue.cue_ball_id

    # Get collisions of the cue ball with the object balls.
    cb_ob_collisions = filter_events(
        shot.events,
        by_type(EventType.BALL_BALL),
        by_ball(cue_id),
    )

    hit_ob_ids = set()
    for event in cb_ob_collisions:
        hit_ob_ids.add(_other(cue_id, event))

        if len(hit_ob_ids) == 2:
            # This is the first (and perhaps only) instance of the cue ball hitting the
            # second object ball.
            second_ob_collision = event
            break
    else:
        # Both object balls were not contacted by the cue ball. No point.
        return False

    # Both balls have been hit by the object ball. But were at least 3 cushions
    # contacted before the second object ball was first hit? If yes, point, otherwise
    # no.

    cushion_hits = filter_events(
        shot.events,
        by_type(EventType.BALL_LINEAR_CUSHION),
        by_ball(cue_id),
        by_time(second_ob_collision.time, after=False),
    )

    return len(cushion_hits) >= 3


def is_turn_over(shot: System, constraints: ShotConstraints) -> bool:
    assert constraints.cueable is not None
    return not is_point(shot)


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
