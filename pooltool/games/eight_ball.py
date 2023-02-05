#! /usr/bin/env python

import pooltool.constants as c
import pooltool.events as e
from pooltool.games.datatypes import Game
from pooltool.layouts import EightBallRack


class EightBall(Game):
    rack = EightBallRack

    def __init__(self, apa_rules=False):
        self.is_call_ball = True
        self.is_call_pocket = True
        Game.__init__(self)
        self.create_players(2)

        self.solids = [str(i) for i in range(1, 8)]
        self.stripes = [str(i) for i in range(9, 16)]

        # Allow stroke mode during break
        self.ball_call = "dummy"
        self.pocket_call = "dummy"

        for player in self.players:
            player.stripes_or_solids = None
            player.target_balls = []
            player.can_cue = ["cue"]

    def start(self, shot):
        self.active_player.ball_in_hand = ["cue"]

    def set_initial_cueing_ball(self, balls):
        return balls["cue"]

    def award_points(self, shot):
        self.shot_info["points"] = {player: 0 for player in self.players}

    def decide_winner(self, shot):
        if self.shot_info["is_legal"]:
            self.winner = self.active_player
        else:
            self.winner = (
                self.players[0]
                if self.players[0] != self.active_player
                else self.players[1]
            )

    def award_ball_in_hand(self, shot):
        if not self.shot_info["is_legal"]:
            self.shot_info["ball_in_hand"] = ["cue"]
            self.respot(
                shot, "cue", shot.table.w / 2, shot.table.l * 1 / 4, shot.balls["cue"].R
            )
        else:
            self.shot_info["ball_in_hand"] = None

    def respot_balls(self, shot):
        pass

    def is_turn_over(self, shot):
        if not self.shot_info["is_legal"]:
            return True

        pocket_events = shot.events.filter_type(e.EventType.BALL_POCKET)

        if self.active_player.stripes_or_solids is None and len(pocket_events):
            return False

        for event in pocket_events:
            ball, pocket = event.agents
            if ball == self.ball_call and pocket == self.pocket_call:
                self.log.add_msg(f"Ball potted: {ball.id}", sentiment="good")
                return False

        return True

    def is_game_over(self, shot):
        pocket_events = shot.events.filter_type(e.EventType.BALL_POCKET)
        for event in pocket_events:
            if "8" in (event.agents[0].id, event.agents[1].id):
                return True

    def is_object_ball_hit_first(self, shot):
        cue = shot.balls["cue"]
        collisions = cue.events.filter_type(e.EventType.BALL_BALL)
        if not len(collisions):
            return False

        first_collision = collisions[0]
        ball1, ball2 = first_collision.agents
        first_ball_hit = ball1 if ball1.id != "cue" else ball2

        if self.active_player.stripes_or_solids is None:
            # stripes or solids not yet determined
            return True

        if first_ball_hit.id in self.active_player.target_balls:
            return True

        return False

    def is_legal_break(self, shot):
        if self.shot_number != 0:
            return True

        ball_pocketed = (
            True if len(shot.events.filter_type(e.EventType.BALL_POCKET)) else False
        )
        enough_cushions = (
            True if len(self.numbered_balls_that_hit_cushion(shot)) >= 4 else False
        )

        return True if (ball_pocketed or enough_cushions) else False

    def numbered_balls_that_hit_cushion(self, shot):
        numbered_balls = [ball for ball in shot.balls.values() if ball.id != "cue"]

        cushion_events = shot.events.filter_type(e.EventType.BALL_CUSHION).filter_ball(
            numbered_balls
        )

        return set([event.agents[0].id for event in cushion_events])

    def is_cue_pocketed(self, shot):
        return True if shot.balls["cue"].s == c.pocketed else False

    def is_cushion_after_first_contact(self, shot):
        if not self.is_object_ball_hit_first(shot):
            return False

        first_contact = shot.balls["cue"].events.filter_type(e.EventType.BALL_BALL)[0]
        cushion_events = shot.events.filter_time(first_contact.time).filter_type(
            e.EventType.BALL_CUSHION
        )

        cushion_hit = True if len(cushion_events) else False

        numbered_balls = [ball for ball in shot.balls.values() if ball.id != "cue"]
        ball_pocketed = shot.events.filter_type(e.EventType.BALL_POCKET).filter_ball(
            numbered_balls
        )

        return True if (cushion_hit or len(ball_pocketed)) else False

    def is_8_ball_sunk_before_others(self, shot):
        if "8" in self.active_player.target_balls:
            return False

        pocket_events = shot.events.filter_type(e.EventType.BALL_POCKET)
        for event in pocket_events:
            if "8" in (event.agents[0].id, event.agents[1].id):
                return True

    def legality(self, shot):
        """Returns whether or not a shot is legal, and the reason"""
        reason = None

        if self.is_8_ball_sunk_before_others(shot):
            reason = "8-ball sunk before others!"
        elif not self.is_object_ball_hit_first(shot):
            reason = "Object ball not hit first"
        elif not self.is_shot_called(shot):
            reason = "No shot called!"
        elif self.is_cue_pocketed(shot):
            reason = "Cue ball in pocket!"
        elif not self.is_cushion_after_first_contact(shot):
            reason = "Cushion not contacted after first contact"
        elif not self.is_legal_break(shot):
            reason = "Must contact 4 rails or pot 1 ball"

        return (True, reason) if not reason else (False, reason)

    def is_shot_called(self, shot):
        if self.shot_number == 0:
            return True

        if self.ball_call is None or self.pocket_call is None:
            return False

        return True

    def advance(self, shot):
        self.update_target_balls(shot)
        self.decide_stripes_or_solids(shot)
        super().advance(shot)

    def update_target_balls(self, shot):
        for player in self.players:
            if self.shot_number == 0:
                player.target_balls = self.solids + self.stripes

            states = [
                ball.s for ball in shot.balls.values() if ball.id in player.target_balls
            ]
            if all([state == c.pocketed for state in states]):
                player.target_balls.append("8")

    def decide_stripes_or_solids(self, shot):
        is_open = True if self.active_player.stripes_or_solids is None else False
        player_potted = not self.shot_info["is_turn_over"]
        is_break_shot = self.shot_number == 0

        if (not is_open) or (not player_potted) or (is_break_shot):
            return

        if self.ball_call.id in self.stripes:
            self.active_player.stripes_or_solids = "stripes"
            self.active_player.target_balls = self.stripes
            other_player = (
                self.players[0]
                if self.players[0] != self.active_player
                else self.players[1]
            )
            other_player.stripes_or_solids = "solids"
            other_player.target_balls = self.solids
        else:
            self.active_player.stripes_or_solids = "solids"
            self.active_player.target_balls = self.solids
            other_player = (
                self.players[0]
                if self.players[0] != self.active_player
                else self.players[1]
            )
            other_player.stripes_or_solids = "stripes"
            other_player.target_balls = self.stripes

        self.log.add_msg(
            f"{self.active_player.name} takes {self.active_player.stripes_or_solids}",
            sentiment="good",
        )
