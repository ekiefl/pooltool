#! /usr/bin/env python

from direct.gui.OnscreenText import OnscreenText
from direct.interval.IntervalGlobal import *
from panda3d.core import *

import pooltool.ani as ani
import pooltool.constants as c
import pooltool.events as e
from pooltool.games import Game, Player
from pooltool.layouts import NineBallRack
from pooltool.objects import DummyBall


class Sandbox(Game):
    def __init__(self, apa_rules=False):
        self.is_call_ball = False
        self.is_call_pocket = False
        Game.__init__(self)
        self.create_players(1)

    def start(self):
        self.active_player.ball_in_hand = [ball_id for ball_id in self.balls]
        for player in self.players:
            player.can_cue = [ball_id for ball_id in self.balls]
            player.target_balls = [ball_id for ball_id in self.balls]

    def setup_initial_layout(self, table, ball_kwargs={}):
        self.balls = NineBallRack(table, ordered=True, **ball_kwargs).balls

    def set_initial_cueing_ball(self, balls):
        return balls["cue"]

    def award_points(self, shot):
        self.shot_info["points"] = {player: 0 for player in self.players}

    def decide_winner(self, shot):
        self.winner = self.active_player

    def award_ball_in_hand(self, shot):
        self.shot_info["ball_in_hand"] = [ball.id for ball in shot.balls.values()]

    def respot_balls(self, shot):
        if shot.balls["cue"].s == c.pocketed:
            self.respot(
                shot, "cue", shot.table.w / 2, shot.table.l * 1 / 4, shot.balls["cue"].R
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
