#! /usr/bin/env python

import pooltool
import pooltool.ani as ani
import pooltool.events as e
import pooltool.ani.utils as autils

from pooltool.games import Player, Game
from pooltool.objects import DummyBall
from pooltool.layouts import NineBallRack

from panda3d.core import *
from direct.interval.IntervalGlobal import *
from direct.gui.OnscreenText import OnscreenText


class Sandbox(Game):
    def __init__(self, apa_rules=False):
        self.is_call_ball = False
        self.is_call_pocket = False
        Game.__init__(self)
        self.create_players(1)

    def start(self):
        self.active_player.ball_in_hand = [ball.id for ball in self.layout.get_balls_dict().values()]
        for player in self.players:
            player.can_cue = [ball.id for ball in self.layout.get_balls_dict().values()]
            player.target_balls = [ball.id for ball in self.layout.get_balls_dict().values()]


    def setup_initial_layout(self, table, ball_kwargs={}):
        self.layout = NineBallRack(ordered=True, **ball_kwargs)
        self.layout.center_by_table(table)

        # get the cueing ball
        self.layout.get_balls_dict()


    def set_initial_cueing_ball(self, balls):
        return balls['cue']


    def award_points(self, shot):
        self.shot_info['points'] = {player: 0 for player in self.players}


    def decide_winner(self, shot):
        self.winner = self.active_player


    def award_ball_in_hand(self, shot):
        self.shot_info['ball_in_hand'] = [ball.id for ball in shot.balls.values()]


    def respot_balls(self, shot):
        if shot.balls['cue'].s == pooltool.pocketed:
            self.respot(shot, 'cue', shot.table.w/2, shot.table.l*1/4, shot.balls['cue'].R)


    def is_turn_over(self, shot):
        return False


    def is_game_over(self, shot):
        return False


    def legality(self, shot):
        """Returns whether or not a shot is legal, and the reason"""
        return (True, None)


    def advance(self, shot):
        super().advance(shot)


