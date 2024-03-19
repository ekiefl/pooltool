#! /usr/bin/env python

from __future__ import annotations

from collections import Counter
from typing import List, Optional, Tuple

from pooltool.ruleset.datatypes import (
    BallInHandOptions,
    Player,
    Ruleset,
    ShotConstraints,
    ShotInfo,
)
from pooltool.ruleset.snooker.balls import BallGroup, ball_info
from pooltool.ruleset.snooker.utils import (
    GamePhase,
    Reason,
    game_phase,
    get_color_balls_to_be_potted,
    get_continued_player_ball_group,
    get_foul_points,
    get_lowest_pottable,
    get_next_player_ball_group,
    is_off_ball_hit_first,
    is_off_ball_pocketed,
    on_final_black,
)
from pooltool.ruleset.utils import (
    get_ball_ids_on_table,
    get_id_of_first_ball_hit,
    get_pocketed_ball_ids_during_shot,
    is_ball_hit,
    is_ball_pocketed,
    respot,
)
from pooltool.system.datatypes import System


def is_legal(shot: System, constraints: ShotConstraints) -> Tuple[bool, Reason]:
    """Was it a legal shot?

    Implemented:
        (1) Failing to hit another ball
        (2) Hitting off-ball first
        (3) Pocketing the cue ball
        (4) Pocketing an off-ball

    Not Implemented:
        (1) Cueing a ball that isn't the cue
        (2) Making ball land off table
        (3) Touching cue ball with anything other than tip of cue
        (4) Playing a push shot (contacting ball moves when cue ball is struck)
        (5) Playing a jump shot
        (6) Playing a shot with both feet off the ground
    """
    if is_ball_pocketed(shot, "white"):
        return False, Reason.CUE_POCKETED
    elif not is_ball_hit(shot):
        return False, Reason.NO_BALL_HIT
    elif is_off_ball_hit_first(shot, constraints):
        return False, Reason.OFF_BALL_HIT_FIRST
    elif is_off_ball_pocketed(shot, constraints):
        return False, Reason.OFF_BALL_POCKETED

    return True, Reason.NONE


def is_turn_over(shot: System, constraints: ShotConstraints, legal: bool) -> bool:
    """Is the player's turn over?

    Not implemented:
        (1) Hit and a miss. Currently, this always leads to end-of-turn
    """
    if not legal:
        return True

    # Get the pocketed on-ball IDs
    pocketed_on_balls = get_pocketed_ball_ids_during_shot(shot)

    if not (num_pocketed := len(pocketed_on_balls)):
        return True

    # Assert cue is not pocketed
    assert "white" not in pocketed_on_balls, "Legal shot has cue in pocket?"

    # Assert no off-balls are pocketed
    assert not is_off_ball_pocketed(
        shot, constraints
    ), "Legal shot w/ off-ball pocketed?"

    # Assert only one ball pocketed if on COLORS
    if BallGroup.get(constraints.hittable) is BallGroup.COLORS:
        assert num_pocketed == 1, "Legal shot has multi colors sank?"

    return False


def is_game_over(shot: System, legal: bool) -> bool:
    """Is the game over?

    Implemented:
        (1) final black ball is potted
        (2) foul on black when black is last
        (3) If it's a tie after black is sunk or scratched on, the game is declared a
            tie. This is NOT a real snooker rule. In real snooker, the black is spotted,
            and a coin toss determines who gets in hand.

    Not implemented:
        (1) Concession of the frame (by losing player)
        (2) Claiming the win (by winning player when on black >7 points ahead)
        (3) Failure to hit 3X in a row (when un-snookered)
    """
    if not on_final_black(shot):
        return False

    if not legal:
        # Foul on black at this stage is an end of frame
        return True

    if "black" in get_pocketed_ball_ids_during_shot(shot, exclude={"white"}):
        return True

    return False


def decide_winner(
    players: List[Player], points: Counter, game_over: bool
) -> Optional[Player]:
    if not game_over:
        return None

    max_points = max(points.values())
    top_players = [name for name, point in points.items() if point == max_points]

    if len(top_players) > 1:
        # More than one player with the highest score indicates a tie
        return None

    player_name = top_players[0]
    for player in players:
        if player.name == player_name:
            return player

    raise ValueError(f"points key '{player_name}' doesn't match passed Player names")


class _Snooker(Ruleset):
    def __init__(self, *args, **kwargs):
        Ruleset.__init__(self, *args, **kwargs)
        self.phase: GamePhase = GamePhase.ALTERNATING

    @property
    def active_group(self):
        return BallGroup.get(self.shot_constraints.hittable)

    def build_shot_info(self, shot: System) -> ShotInfo:
        legal, reason = is_legal(shot, self.shot_constraints)
        turn_over = is_turn_over(shot, self.shot_constraints, legal)
        game_over = is_game_over(shot, legal)
        score = self.get_score(shot, turn_over, legal)
        winner = decide_winner(self.players, score, game_over)

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
            ball_in_hand=BallInHandOptions.SEMICIRCLE,
            movable=["white"],
            cueable=["white"],
            hittable=BallGroup.REDS.balls,
            call_shot=False,
        )

    def next_shot_constraints(self, shot: System) -> ShotConstraints:
        self.phase = game_phase(shot, self.shot_info.legal)

        gets_ball_in_hand = "white" in get_pocketed_ball_ids_during_shot(shot)

        if self.shot_info.turn_over:
            ball_group = get_next_player_ball_group(shot)
        else:
            ball_group = get_continued_player_ball_group(shot, self.shot_constraints)

        if self.phase is GamePhase.ALTERNATING:
            hittable = ball_group.balls
            call_shot = True if ball_group is BallGroup.COLORS else False
            ball_call = None
        else:
            lowest = get_lowest_pottable(shot)
            hittable = (lowest,)
            call_shot = True
            ball_call = lowest

        # FIXME Currently, the GUI requires calling a pocket in addition to a ball.
        # Ideally, games could be made where a ball is called without a pocket. Until
        # then, just choose any pocket
        pocket_call = "lb"

        return ShotConstraints(
            ball_in_hand=(
                BallInHandOptions.SEMICIRCLE
                if gets_ball_in_hand
                else BallInHandOptions.NONE
            ),
            movable=["white"] if gets_ball_in_hand else [],
            cueable=["white"],
            hittable=hittable,
            call_shot=call_shot,
            ball_call=ball_call,
            pocket_call=pocket_call,
        )

    def respot_balls(self, shot: System):
        check: List[str] = ["white"]

        if self.phase is GamePhase.ALTERNATING:
            check.extend(list(BallGroup.COLORS.balls))
        else:
            assert (ball_call := self.shot_constraints.ball_call) is not None
            check.extend(
                get_color_balls_to_be_potted(
                    shot,
                    self.shot_info.legal,
                    ball_call,
                )
            )

        on_table = get_ball_ids_on_table(shot, at_start=False)
        for ball_id in check:
            if ball_id not in on_table:
                ideal_relative_coords = ball_info(ball_id).respot
                assert ideal_relative_coords is not None

                ideal_x = ideal_relative_coords[0] * shot.table.w
                ideal_y = ideal_relative_coords[1] * shot.table.l

                respot(shot, ball_id, ideal_x, ideal_y)

    def get_score(self, shot: System, turn_over: bool, legal: bool) -> Counter:
        if legal and turn_over:
            return self.score
        elif legal and not turn_over:
            potted_ids = get_pocketed_ball_ids_during_shot(shot)
            assert "white" not in potted_ids, "Legal shot with white ball pocketed?"

            if self.active_group is BallGroup.REDS:
                for ball_id in potted_ids:
                    assert ball_id in BallGroup.REDS.balls, "Legal shot with non-red?"
                    self.score[self.active_player.name] += ball_info(ball_id).points
            else:
                assert len(potted_ids) == 1, "Only one ball can be potted on colors"
                ball_id = potted_ids[0]
                assert ball_id in BallGroup.COLORS.balls
                self.score[self.active_player.name] += ball_info(ball_id).points
        else:
            offending_balls = set(get_pocketed_ball_ids_during_shot(shot))
            offending_balls.add("white")
            if (first_hit := get_id_of_first_ball_hit(shot, cue="white")) is not None:
                offending_balls.add(first_hit)
            if self.shot_constraints.call_shot:
                assert self.shot_constraints.ball_call is not None
                offending_balls.add(self.shot_constraints.ball_call)

            self.score[self.last_player.name] += get_foul_points(offending_balls)

        return self.score

    def process_shot(self, shot: System):
        """Override process_shot to add log messages"""
        super().process_shot(shot)

        ball_ids = get_pocketed_ball_ids_during_shot(shot, exclude={"white"})
        if len(ball_ids):
            sentiment = "neutral" if self.shot_info.turn_over else "good"
            self.log.add_msg(
                f"Ball(s) potted: {', '.join(ball_ids)}", sentiment=sentiment
            )

        if not self.shot_info.legal:
            self.log.add_msg(f"Illegal shot! {self.shot_info.reason}", sentiment="bad")

        if self.shot_info.turn_over:
            self.log.add_msg(
                f"{self.last_player.name} is up!",
                sentiment="good",
            )

    def copy(self) -> _Snooker:
        raise NotImplementedError("Snooker copy needs to be implemented")
