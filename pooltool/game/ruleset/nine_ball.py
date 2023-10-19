#! /usr/bin/env python

from collections import Counter
from typing import Optional, Set, Tuple

import pooltool.constants as c
import pooltool.events as events
from pooltool.events.datatypes import EventType
from pooltool.game.ruleset.datatypes import Ruleset
from pooltool.objects.ball.datatypes import Ball
from pooltool.system.datatypes import System


class NineBall(Ruleset):
    def __init__(self):
        Ruleset.__init__(self, False, False, None)

    def start(self, _: System):
        self.active_player.ball_in_hand = "cue"

    def get_initial_cueing_ball(self, balls) -> Ball:
        return balls["cue"]

    def award_points(self, _: System) -> Counter:
        return Counter()

    def decide_winner(self, _: System) -> None:
        self.winner = self.active_player

    def award_ball_in_hand(self, shot: System, legal) -> Optional[str]:
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

    def respot_balls(self, shot: System) -> None:
        highest = self.get_highest_ball(shot)
        lowest = self.get_lowest_ball(shot)

        pocket_events = events.filter_type(shot.events, EventType.BALL_POCKET)
        pocketed_balls = [event.agents[0] for event in pocket_events]

        if (
            (highest == lowest)
            and (highest in pocketed_balls)
            and not self.shot_info.is_legal
        ):
            self.respot(
                shot,
                highest.id,
                shot.table.w / 2,
                shot.table.l * 3 / 4,
                highest.R,
            )

    def is_turn_over(self, shot: System) -> bool:
        legal, _ = self.legality(shot)
        if not legal:
            return True

        pocket_events = events.filter_type(shot.events, EventType.BALL_POCKET)
        if len(pocket_events):
            balls_potted = [e.agents[0].id for e in pocket_events]
            self.log.add_msg(
                f"Ball(s) potted: {','.join(balls_potted)}", sentiment="good"
            )
            return False

        return True

    def is_game_over(self, shot: System) -> bool:
        highest = self.get_highest_ball(shot)

        pocket_events = events.filter_type(shot.events, EventType.BALL_POCKET)
        pocketed_balls = [event.agents[0] for event in pocket_events]

        if highest in pocketed_balls and self.shot_info.is_legal:
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
        lowest = self.get_lowest_ball(shot)
        cue = shot.balls["cue"]

        cue_ball_events = events.filter_ball(shot.events, cue.id)
        collisions = events.filter_type(cue_ball_events, EventType.BALL_BALL)

        return bool(len(collisions)) and lowest in collisions[0].agents

    def is_legal_break(self, shot: System) -> bool:
        if self.shot_number != 0:
            return True

        ball_pocketed = bool(
            len(events.filter_type(shot.events, EventType.BALL_POCKET))
        )
        enough_cushions = len(self.numbered_balls_that_hit_cushion(shot)) >= 4

        return ball_pocketed or enough_cushions

    def numbered_balls_that_hit_cushion(self, shot: System) -> Set[str]:
        numbered_balls = [ball.id for ball in shot.balls.values() if ball.id != "cue"]

        cushion_events = events.filter_type(
            shot.events,
            [EventType.BALL_LINEAR_CUSHION, EventType.BALL_CIRCULAR_CUSHION],
        )
        numbered_ball_cushion_events = events.filter_ball(
            cushion_events, numbered_balls
        )

        return set([event.agents[0].id for event in numbered_ball_cushion_events])

    def is_cue_pocketed(self, shot: System) -> bool:
        return shot.balls["cue"].state.s == c.pocketed

    def is_cushion_after_first_contact(self, shot: System) -> bool:
        if not self.is_lowest_hit_first(shot):
            return False

        cue_events = events.filter_ball(shot.events, shot.balls["cue"].id)
        first_contact = events.filter_type(cue_events, EventType.BALL_BALL)[0]
        after_first_contact = events.filter_time(cue_events, first_contact.time)
        cushion_events = events.filter_type(
            after_first_contact,
            [EventType.BALL_LINEAR_CUSHION, EventType.BALL_CIRCULAR_CUSHION],
        )

        cushion_hit = bool(len(cushion_events))

        numbered_balls = [ball.id for ball in shot.balls.values() if ball.id != "cue"]

        balls_pocketed = events.filter_type(shot.events, EventType.BALL_POCKET)
        numbered_balls_pocketed = events.filter_ball(balls_pocketed, numbered_balls)

        return cushion_hit or bool(len(numbered_balls_pocketed))

    def legality(self, shot: System) -> Tuple[bool, str]:
        """Returns whether or not a shot is legal, and the reason"""
        reason = ""

        if not self.is_lowest_hit_first(shot):
            reason = "Lowest ball not hit first"
        elif self.is_cue_pocketed(shot):
            reason = "Cue ball in pocket!"
        elif not self.is_cushion_after_first_contact(shot):
            reason = "Cushion not contacted after first contact"
        elif not self.is_legal_break(shot):
            reason = "Must contact 4 rails or pot 1 ball"

        return (True, reason) if not reason else (False, reason)
