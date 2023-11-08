#! /usr/bin/env python

from __future__ import annotations

from collections import Counter
from typing import List, Optional, Tuple

from pooltool.game.ruleset.datatypes import (
    BallInHandOptions,
    Player,
    Ruleset,
    ShotConstraints,
    ShotInfo,
)
from pooltool.game.ruleset.snooker.utils import (
    BallGroup,
    is_off_ball_hit_first,
    is_off_ball_pocketed,
    on_final_black,
)
from pooltool.game.ruleset.utils import (
    get_ball_ids_on_table,
    get_pocketed_ball_ids_during_shot,
    is_ball_hit,
    is_ball_pocketed,
)
from pooltool.system.datatypes import System


def is_legal(shot: System, constraints: ShotConstraints) -> Tuple[bool, str]:
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
    reason = ""
    legal = True
    if is_ball_pocketed(shot, "white"):
        legal = False
        reason = "Cue ball in pocket!"
    elif not is_ball_hit(shot):
        legal = False
        reason = "No ball contacted!"
    elif is_off_ball_hit_first(shot, constraints):
        legal = False
        reason = "First contact wasn't made with target balls!"
    elif is_off_ball_pocketed(shot, constraints):
        legal = False
        reason = "Off-ball was pocketed!"

    return legal, reason


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
    assert is_off_ball_pocketed(shot, constraints), "Legal shot w/ off-ball pocketed?"

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

    player_name = max(points, key=lambda x: points[x])
    for player in players:
        if player.name == player_name:
            return player

    raise ValueError(f"points key '{player_name}' doesn't match passed Player names")


class Snooker(Ruleset):
    def build_shot_info(self, shot: System) -> ShotInfo:
        legal, reason = is_legal(shot, self.shot_constraints)
        turn_over = is_turn_over(shot, self.shot_constraints, legal)
        game_over = is_game_over(shot, legal)
        score = self.get_score(shot)
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
            ball_in_hand=BallInHandOptions.IN_THE_D,
            movable=["white"],
            cueable=["white"],
            hittable=BallGroup.REDS.balls,
            call_shot=False,
        )

    def next_shot_constraints(self, shot: System) -> ShotConstraints:
        gets_ball_in_hand = (
            False if "white" in get_ball_ids_on_table(shot, at_start=False) else True
        )

        curr_group = BallGroup.get(self.shot_constraints.hittable)
        next_group = (
            curr_group.next(shot)
            if self.shot_info.turn_over
            else curr_group.cont(shot, self.shot_constraints)
        )

        return ShotConstraints(
            ball_in_hand=(
                BallInHandOptions.NONE
                if gets_ball_in_hand
                else BallInHandOptions.IN_THE_D
            ),
            movable=["white"] if gets_ball_in_hand else [],
            cueable=["white"],
            hittable=next_group.balls,
            call_shot=True if next_group is BallGroup.COLORS else False,
        )

    def respot_balls(self, shot: System):
        pass

    def get_score(self, shot: System) -> Counter:
        return Counter()
