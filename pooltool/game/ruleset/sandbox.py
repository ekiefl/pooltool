#! /usr/bin/env python

import pooltool.constants as c
from pooltool.game.ruleset.datatypes import Game
from pooltool.layouts import NineBallRack


class Sandbox(Game):
    rack = NineBallRack

    def __init__(self, apa_rules=False):
        self.is_call_ball = False
        self.is_call_pocket = False
        Game.__init__(self)
        self.create_players(1)

    def start(self, shot):
        self.active_player.ball_in_hand = [ball_id for ball_id in shot.balls]
        for player in self.players:
            player.can_cue = [ball_id for ball_id in shot.balls]
            player.target_balls = [ball_id for ball_id in shot.balls]

    def get_initial_cueing_ball(self, balls):
        return balls["cue"]

    def award_points(self, shot):
        self.shot_info["points"] = {player: 0 for player in self.players}

    def decide_winner(self, shot):
        self.winner = self.active_player

    def award_ball_in_hand(self, shot):
        self.shot_info["ball_in_hand"] = [ball.id for ball in shot.balls.values()]

    def respot_balls(self, shot):
        if shot.balls["cue"].state.s == c.pocketed:
            self.respot(
                shot,
                "cue",
                shot.table.w / 2,
                shot.table.l * 1 / 4,
                shot.balls["cue"].params.R,
            )

    def is_turn_over(self, shot):
        return False

    def is_game_over(self, shot):
        return False

    def legality(self, shot):
        """Returns whether or not a shot is legal, and the reason"""
        return (True, None)

    def advance(self, shot):
        super().advance(shot)
