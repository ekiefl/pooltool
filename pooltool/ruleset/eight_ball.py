#! /usr/bin/env python

from __future__ import annotations

from typing import Counter, Dict, Optional, Tuple

from pooltool.events.datatypes import EventType
from pooltool.events.filter import by_ball, by_time, by_type, filter_events
from pooltool.ruleset.datatypes import (
    BallInHandOptions,
    Player,
    Ruleset,
    ShotConstraints,
    ShotInfo,
)
from pooltool.ruleset.utils import (
    balls_that_hit_cushion,
    get_pocketed_ball_ids,
    get_pocketed_ball_ids_during_shot,
    is_ball_hit,
    is_ball_pocketed,
    is_ball_pocketed_in_pocket,
    is_numbered_ball_pocketed,
    is_shot_called_if_required,
    is_target_group_hit_first,
    respot,
)
from pooltool.system.datatypes import System
from pooltool.utils.strenum import StrEnum, auto


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


def _is_8_ball_pocketed_incorrectly(shot: System, constraints: ShotConstraints) -> bool:
    if not is_ball_pocketed(shot, "8"):
        # 8-ball is not pocketed, no problems here
        return False

    if "8" not in constraints.hittable:
        # Pocketed out-of-turn
        return True

    ball_id, pocket_id = filter_events(
        shot.events,
        by_type(EventType.BALL_POCKET),
        by_ball("8"),
    )[0].ids

    assert ball_id == "8"

    return pocket_id != constraints.pocket_call


def get_next_hittable_balls(
    shot: System, constraints: ShotConstraints, info: ShotInfo
) -> Tuple[str, ...]:
    turn_over = info.turn_over
    curr_group = BallGroup.get(constraints.hittable)
    ball_call = constraints.ball_call

    if turn_over:
        return curr_group.next(shot).balls

    return curr_group.cont(shot, ball_call).balls


def is_legal(
    shot: System,
    constraints: ShotConstraints,
    break_shot: bool,
) -> Tuple[bool, str]:
    """Returns whether or not a shot is legal, and the reason"""
    if break_shot:
        return _is_legal_break(shot)

    cushion_after_contact = _is_cushion_hit_after_first_contact(shot)
    ball_pocketed = is_numbered_ball_pocketed(shot)

    reason = ""
    legal = True
    if is_ball_pocketed(shot, "cue"):
        legal = False
        reason = "Cue ball in pocket!"
    elif not is_ball_hit(shot):
        legal = False
        reason = "No ball contacted"
    elif not is_target_group_hit_first(shot, constraints.hittable, "cue"):
        legal = False
        reason = "First contact wasn't made with target balls"
    elif not cushion_after_contact and not ball_pocketed:
        legal = False
        reason = "Cushion not contacted after first contact"
    elif not is_shot_called_if_required(constraints):
        legal = False
        reason = "Shot not called, but it was required!"

    # Game ender
    if _is_8_ball_pocketed_incorrectly(shot, constraints):
        legal = False
        reason = "8-ball sunk illegally (out of turn or wrong pocket)!"

    return legal, reason


def is_turn_over(shot: System, constraints: ShotConstraints, legal: bool) -> bool:
    if not legal:
        return True

    ids = get_pocketed_ball_ids_during_shot(shot)
    assert "cue" not in ids, "Legal shot has cue in pocket?"

    # Break shot case
    if not constraints.call_shot:
        return not any(ball_id in constraints.hittable for ball_id in ids)

    assert constraints.ball_call is not None
    assert constraints.pocket_call is not None

    if is_ball_pocketed_in_pocket(shot, constraints.ball_call, constraints.pocket_call):
        return False

    return True


def is_game_over(shot: System) -> bool:
    return is_ball_pocketed(shot, "8")


def decide_winner(
    game_over: bool, legal: bool, active: Player, other: Player
) -> Optional[Player]:
    if not game_over:
        return None

    return active if legal else other


class _EightBall(Ruleset):
    @property
    def active_group(self) -> BallGroup:
        return BallGroup.get(self.shot_constraints.hittable)

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
            shooting = self.active_group.next(shot)
            self.log.add_msg(
                f"{self.last_player.name} is up! Aiming at: {shooting}",
                sentiment="good",
            )

    def build_shot_info(self, shot: System) -> ShotInfo:
        legal, reason = is_legal(shot, self.shot_constraints, self.shot_number == 0)
        turn_over = is_turn_over(shot, self.shot_constraints, legal)
        game_over = is_game_over(shot)
        winner = decide_winner(game_over, legal, self.active_player, self.last_player)
        score = self.get_score(shot)

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
            hittable=BallGroup.UNDECIDED.balls,
            call_shot=False,
        )

    def next_shot_constraints(self, shot: System) -> ShotConstraints:
        if self.shot_info.legal:
            ball_in_hand = BallInHandOptions.NONE
            movable = []
        else:
            ball_in_hand = BallInHandOptions.ANYWHERE
            movable = ["cue"]

        hittable = get_next_hittable_balls(shot, self.shot_constraints, self.shot_info)

        return ShotConstraints(
            ball_in_hand=ball_in_hand,
            movable=movable,
            cueable=["cue"],
            hittable=hittable,
            call_shot=True,
        )

    def get_score(self, shot: System) -> Counter:
        """How many stripes/solids are down?"""
        other_group = self.active_group.next(shot)

        if self.active_group is BallGroup.UNDECIDED:
            # No points before solids/stripes is determined
            assert other_group is BallGroup.UNDECIDED
            return Counter()

        pocketed = get_pocketed_ball_ids(shot)
        num_stripes = sum(ball in BallGroup.STRIPES.balls for ball in pocketed)
        num_solids = sum(ball in BallGroup.SOLIDS.balls for ball in pocketed)

        if self.active_group is BallGroup.SOLIDS:
            return Counter(
                {
                    self.active_player.name: num_solids,
                    self.last_player.name: num_stripes,
                }
            )
        elif self.active_group is BallGroup.STRIPES:
            return Counter(
                {
                    self.active_player.name: num_stripes,
                    self.last_player.name: num_solids,
                }
            )
        elif self.active_group is BallGroup.EIGHT:
            if num_solids == 7:
                num_active = num_solids
                num_other = num_stripes
            else:
                num_active = num_stripes
                num_other = num_solids

            assert (ball_call := self.shot_constraints.ball_call) == "8"
            assert (pocket_call := self.shot_constraints.pocket_call) is not None
            if (
                is_ball_pocketed_in_pocket(shot, ball_call, pocket_call)
                and self.shot_info.legal
            ):
                num_active += 1

            return Counter(
                {self.active_player.name: num_active, self.last_player.name: num_other}
            )
        else:
            raise NotImplementedError(f"Unknown: {self.active_group}")

    def respot_balls(self, shot: System):
        """No balls respotted in this variant of 8-ball"""
        if not self.shot_info.legal:
            respot(
                shot,
                "cue",
                shot.table.w / 2,
                shot.table.l * 1 / 4,
            )

    def copy(self) -> _EightBall:
        raise NotImplementedError("EightBall copy needs to be implemented")


class BallGroup(StrEnum):
    SOLIDS = auto()
    STRIPES = auto()
    UNDECIDED = auto()
    EIGHT = auto()

    @property
    def balls(self) -> Tuple[str, ...]:
        """Return the ball IDs associated to a BallGroup"""
        return _group_to_balls_dict[self]

    def next(self, shot: System) -> BallGroup:
        """Get next player's ball-group"""

        if self is BallGroup.UNDECIDED:
            return BallGroup.UNDECIDED

        pocketed = get_pocketed_ball_ids(shot)
        stripes_done = sum(ball in BallGroup.STRIPES.balls for ball in pocketed) == 7
        solids_done = sum(ball in BallGroup.SOLIDS.balls for ball in pocketed) == 7

        if self is BallGroup.STRIPES:
            return BallGroup.SOLIDS if not solids_done else BallGroup.EIGHT

        if self is BallGroup.SOLIDS:
            return BallGroup.STRIPES if not stripes_done else BallGroup.EIGHT

        if self is BallGroup.EIGHT:
            if stripes_done and solids_done:
                # Both players on 8-ball
                return BallGroup.EIGHT
            elif stripes_done:
                return BallGroup.SOLIDS
            elif solids_done:
                return BallGroup.STRIPES
            else:
                raise ValueError(
                    "Currently BallGroup.EIGHT, but neither solids nor stripes are done"
                )

        raise NotImplementedError(f"{self} unknown to method `other`.")

    def cont(self, shot: System, ball_call: Optional[str]) -> BallGroup:
        """Get the same player's ball-group for next shot"""
        if ball_call is None:
            # This is the break shot (it's illegal not to call a ball on every shot
            # except the break). Solids/stripes is yet to be determined.
            assert self is BallGroup.UNDECIDED
            return self

        if self is BallGroup.EIGHT:
            # Player remains on EIGHT until end of game (this clause would never be met
            # under standard circumstances, since when the player is on EIGHT, they
            # either end their turn, or win the game)
            return self

        stripes = BallGroup.STRIPES.balls
        solids = BallGroup.SOLIDS.balls

        if self is BallGroup.UNDECIDED:
            # The player potted a called ball, solidifying stripes/solids
            assert ball_call is not None
            if ball_call in stripes:
                group = BallGroup.STRIPES
            elif ball_call in solids:
                group = BallGroup.SOLIDS
            else:
                raise ValueError(
                    "Cannot call anything but STRIPES or SOLIDS when UNDECIDED"
                )
        else:
            # Player was on stripes/solids and continues to be on stripes/solids
            group = self

        # At this point, group is either SOLIDS or STRIPES
        assert group in (BallGroup.SOLIDS, BallGroup.STRIPES)

        # Upgrade group to EIGHT if all balls have been potted
        pocketed = get_pocketed_ball_ids(shot)
        if group is BallGroup.STRIPES:
            stripes_done = sum(ball in stripes for ball in pocketed) == 7
            group = BallGroup.EIGHT if stripes_done else group
        elif group is BallGroup.SOLIDS:
            solids_done = sum(ball in solids for ball in pocketed) == 7
            group = BallGroup.EIGHT if solids_done else group

        return group

    @classmethod
    def get(cls, balls: Tuple[str, ...]) -> BallGroup:
        return _balls_to_group_dict[balls]


_group_to_balls_dict: Dict[BallGroup, Tuple[str, ...]] = {
    BallGroup.SOLIDS: tuple(str(i) for i in range(1, 8)),
    BallGroup.STRIPES: tuple(str(i) for i in range(9, 16)),
    BallGroup.UNDECIDED: tuple(str(i) for i in range(1, 16) if i != 8),
    BallGroup.EIGHT: ("8",),
}

_balls_to_group_dict: Dict[Tuple[str, ...], BallGroup] = {
    v: k for k, v in _group_to_balls_dict.items()
}
