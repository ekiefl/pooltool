#! /usr/bin/env python

import pooltool

from pooltool.terminal import Timer

import uuid

from abc import ABC, abstractmethod
from collections import deque
from panda3d.core import *
from direct.interval.IntervalGlobal import *
from direct.gui.OnscreenText import OnscreenText

class Log(object):
    def __init__(self):
        self.timer = Timer()
        self.log = []

        self.top_spot = 0.9
        self.spacer = 0.06
        self.scale1 = 0.06
        self.scale2 = 0.04

        self.on_screen = deque([])
        self.on_screen_max = 5
        for i in range(self.on_screen_max):
            self.on_screen.append(self.init_text_object(i))


    def init_text_object(self, i, scale=0.07, msg=""):
        return OnscreenText(
            text=msg,
            pos=(-1.5, self.top_spot-self.spacer*i),
            scale=scale,
            fg=(1, 0.5, 0.5, 1),
            align=TextNode.ALeft,
            mayChange=True
        )


    def broadcast_msg(self, msg):
        self.on_screen.appendleft(self.init_text_object(-1, msg=msg))

        off_screen = self.on_screen.pop()
        off_screen.hide()
        del off_screen

        animation = Parallel()
        for i, on_screen_text in enumerate(self.on_screen):
            sequence = Sequence(
                Wait(0.2),
                LerpFunctionInterval(
                    on_screen_text.setY,
                    toData = self.top_spot-self.spacer*i,
                    fromData = self.top_spot-self.spacer*(i-1),
                    duration = 0.5
                ),
            )
            if i == 0:
                sequence = Parallel(
                    sequence,
                    LerpFunctionInterval(
                        on_screen_text.setAlphaScale,
                        toData = 1,
                        fromData = 0,
                        duration = 0.5
                    ),
                )
            elif i == 1:
                sequence = Parallel(
                    sequence,
                    LerpFunctionInterval(
                        on_screen_text.setScale,
                        toData = self.scale2,
                        fromData = self.scale1,
                        duration = 0.5
                    ),
                )
            elif i == self.on_screen_max - 1:
                sequence = Parallel(
                    sequence,
                    LerpFunctionInterval(
                        on_screen_text.setAlphaScale,
                        toData = 0,
                        fromData = 1,
                        duration = 0.5
                    ),
                )
            animation.append(sequence)
        animation.start()


    def add_msg(self, msg, quiet=False):
        self.log.append({
            'time': self.timer.timestamp(),
            'msg': msg,
            'quiet': quiet,
        })

        if not quiet:
            self.broadcast_msg(msg)


class Game(ABC, Log):
    def __init__(self):
        self.players = None
        self.shot_number = None
        self.turn_number = None
        self.active_player = None
        self.game_over = None
        self.winner = None
        self.tie = False
        self.ball_in_hand = None

        Log.__init__(self)


    def create_players(self, num_players):
        self.players = []
        for n in range(1, num_players+1):
            player = Player()
            player.set_name(f"Player {n}")
            self.players.append(player)


    def init(self):
        self.shot_number = 0
        self.turn_number = 0
        self.set_next_player()
        self.game_over = False
        self.winner = None
        self.tie = False
        self.ball_in_hand = None


    def set_next_player(self):
        next_player = self.players[self.turn_number % len(self.players)]
        if next_player != self.active_player:
            self.last_player, self.active_player = self.active_player, next_player
            self.active_player.is_shooting = True
            if self.last_player:
                self.last_player.is_shooting = False

            self.add_msg(f"{self.active_player.name} is up")


    def process_shot(self, shot):
        self.shot_info = {}
        self.shot_info['is_legal'], self.shot_info['reason'] = self.legality(shot)
        if self.shot_info['is_legal']:
            self.add_msg("The shot was legal.", quiet=True)
        else:
            self.add_msg(f"The shot was illegal! {self.shot_info['reason']}")
        self.shot_info['is_turn_over'] = self.is_turn_over(shot)

        self.award_points(shot)
        self.award_ball_in_hand(shot)
        self.respot_balls(shot)


    def respot(self, shot, ball_id, x, y, z):
        """Move cue ball to head spot or close to"""
        R = shot.balls[ball_id].R
        shot.balls[ball_id].rvw[0] = [x, y, z]
        shot.balls[ball_id].s = pooltool.stationary


    def advance(self, shot):
        for player in self.players:
            player.points += self.shot_info['points'][player]
            self.add_msg(f"{player.name} points: {player.points}", quiet=True)

        if self.is_game_over(shot):
            self.game_over = True
            self.decide_winner(shot)
            self.add_msg(f"Game over! The winner was {self.winner.name}")
            return

        if self.shot_info['is_turn_over']:
            self.turn_number += 1
        self.shot_number += 1

        self.set_next_player()


    @abstractmethod
    def legality(self, shot):
        pass


    @abstractmethod
    def award_points(self, shot):
        pass


    @abstractmethod
    def respot_balls(self, shot):
        pass


    @abstractmethod
    def is_game_over(self, shot):
        pass


    @abstractmethod
    def award_ball_in_hand(self, shot):
        pass

    @abstractmethod
    def is_turn_over(self, shot):
        pass


    @abstractmethod
    def decide_winner(self, shot):
        pass


class Player(object):
    def __init__(self):
        self.id = uuid.uuid4().hex
        self.name = None
        self.is_shooting = False
        self.points = 0


    def set_name(self, name):
        self.name = name















