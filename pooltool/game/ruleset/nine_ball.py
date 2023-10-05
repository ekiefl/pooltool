#! /usr/bin/env python

import pooltool.constants as c
import pooltool.events as e
from pooltool.game.layouts import NineBallRack
from pooltool.game.ruleset.datatypes import Ruleset
from pooltool.objects.ball.datatypes import Ball


class NineBall(Ruleset):
    rack = NineBallRack

    def __init__(self, apa_rules=False):
        self.is_call_ball = False
        self.is_call_pocket = False
        Ruleset.__init__(self)
        self.apa_rules = apa_rules
        self.create_players(2)

    def start(self, shot):
        self.active_player.ball_in_hand = ["cue"]

    def get_initial_cueing_ball(self, balls):
        return balls["cue"]

    def award_points(self, shot):
        """APA-style points"""
        self.shot_info["points"] = {player: 0 for player in self.players}

        if not self.shot_info["is_legal"]:
            return

        points = 0
        for event in e.filter_type(shot.events, e.EventType.BALL_POCKET):
            ball, pocket = event.agents
            points += 2 if (ball.id == "9") else 1

        self.shot_info["points"][self.active_player] = points

    def decide_winner(self, shot):
        if self.apa_rules:
            if self.players[0].points == self.players[1].points:
                self.winner = None
                self.tie = True
            else:
                self.winner = max(self.players, key=lambda x: x.points)
        else:
            self.winner = self.active_player

    def award_ball_in_hand(self, shot):
        if not self.shot_info["is_legal"]:
            self.shot_info["ball_in_hand"] = ["cue"]
            self.respot(
                shot, "cue", shot.table.w / 2, shot.table.l * 1 / 4, shot.balls["cue"].R
            )
        else:
            self.shot_info["ball_in_hand"] = None

    def respot_balls(self, shot):
        highest = self.get_highest_ball(shot)
        lowest = self.get_lowest_ball(shot)

        pocket_events = e.filter_type(shot.events, e.EventType.BALL_POCKET)
        pocketed_balls = [event.agents[0] for event in pocket_events]

        if (
            (highest == lowest)
            and (highest in pocketed_balls)
            and not self.shot_info["is_legal"]
        ):
            self.respot(
                shot, highest.id, shot.table.w / 2, shot.table.l * 3 / 4, highest.R
            )

    def is_turn_over(self, shot):
        if not self.shot_info["is_legal"]:
            return True

        pocket_events = e.filter_type(shot.events, e.EventType.BALL_POCKET)
        if len(pocket_events):
            balls_potted = [e.agents[0].id for e in pocket_events]
            self.log.add_msg(
                f"Ball(s) potted: {','.join(balls_potted)}", sentiment="good"
            )
            return False

        return True

    def is_game_over(self, shot):
        highest = self.get_highest_ball(shot)

        pocket_events = e.filter_type(shot.events, e.EventType.BALL_POCKET)
        pocketed_balls = [event.agents[0] for event in pocket_events]

        if highest in pocketed_balls and self.shot_info["is_legal"]:
            return True
        else:
            return False

    def get_lowest_ball(self, shot):
        lowest = Ball.dummy(id="10")

        for ball in shot.balls.values():
            if ball.id == "cue":
                continue
            if ball.history.s[0] == c.pocketed:
                continue
            if int(ball.id) < int(lowest.id):
                lowest = ball

        return lowest

    def get_highest_ball(self, shot):
        highest = Ball.dummy(id="0")

        for ball in shot.balls.values():
            if ball.id == "cue":
                continue
            if ball.history.s[0] == c.pocketed:
                continue
            if int(ball.id) > int(highest.id):
                highest = ball

        return highest

    def is_lowest_hit_first(self, shot):
        lowest = self.get_lowest_ball(shot)
        cue = shot.balls["cue"]

        cue_ball_events = e.filter_ball(shot.events, cue.id)
        collisions = e.filter_type(cue_ball_events, e.EventType.BALL_BALL)

        return True if (len(collisions) and lowest in collisions[0].agents) else False

    def is_legal_break(self, shot):
        if self.shot_number != 0:
            return True

        ball_pocketed = (
            True if len(e.filter_type(shot.events, e.EventType.BALL_POCKET)) else False
        )
        enough_cushions = (
            True if len(self.numbered_balls_that_hit_cushion(shot)) >= 4 else False
        )

        return True if (ball_pocketed or enough_cushions) else False

    def numbered_balls_that_hit_cushion(self, shot):
        numbered_balls = [ball.id for ball in shot.balls.values() if ball.id != "cue"]

        cushion_events = e.filter_type(
            shot.events,
            [e.EventType.BALL_LINEAR_CUSHION, e.EventType.BALL_CIRCULAR_CUSHION],
        )
        numbered_ball_cushion_events = e.filter_ball(cushion_events, numbered_balls)

        return set([event.agents[0].id for event in numbered_ball_cushion_events])

    def is_cue_pocketed(self, shot):
        return shot.balls["cue"].s == c.pocketed

    def is_cushion_after_first_contact(self, shot):
        if not self.is_lowest_hit_first(shot):
            return False

        cue_events = e.filter_ball(shot.events, shot.balls["cue"].id)
        first_contact = e.filter_type(cue_events, e.EventType.BALL_BALL)[0]
        after_first_contact = e.filter_time(first_contact.time)
        cushion_events = e.filter_type(
            after_first_contact,
            [e.EventType.BALL_LINEAR_CUSHION, e.EventType.BALL_CIRCULAR_CUSHION],
        )

        cushion_hit = True if len(cushion_events) else False

        numbered_balls = [ball.id for ball in shot.balls.values() if ball.id != "cue"]

        balls_pocketed = e.filter_type(shot.events, e.EventType.BALL_POCKET)
        numbered_balls_pocketed = e.filter_ball(balls_pocketed, numbered_balls)

        return True if (cushion_hit or len(numbered_balls_pocketed)) else False

    def legality(self, shot):
        """Returns whether or not a shot is legal, and the reason"""
        reason = None

        if not self.is_lowest_hit_first(shot):
            reason = "Lowest ball not hit first"
        elif self.is_cue_pocketed(shot):
            reason = "Cue ball in pocket!"
        elif not self.is_cushion_after_first_contact(shot):
            reason = "Cushion not contacted after first contact"
        elif not self.is_legal_break(shot):
            reason = "Must contact 4 rails or pot 1 ball"

        return (True, reason) if not reason else (False, reason)
