#! /usr/bin/env python

import pooltool

from pooltool.terminal import Timer

import uuid

from abc import ABC, abstractmethod

class Log(object):
    def __init__(self):
        self.timer = Timer()
        self.msgs = []


    def add_msg(self, msg, sentiment='neutral', quiet=False):
        self.msgs.append({
            'time': self.timer.timestamp(),
            'elapsed': self.timer.time_elapsed(fmt="{minutes}:{seconds}"),
            'msg': msg,
            'quiet': quiet,
            'sentiment': sentiment,
            'broadcast': False
        })

        if not quiet:
            self.update = True


class Game(ABC):
    def __init__(self):
        self.players = None
        self.shot_number = None
        self.turn_number = None
        self.active_player = None
        self.game_over = None
        self.winner = None
        self.tie = False
        self.ball_in_hand = None

        self.log = Log()


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

            self.log.add_msg(f"{self.active_player.name} is up", sentiment='neutral')


    def process_shot(self, shot):
        self.shot_info = {}
        self.shot_info['is_legal'], self.shot_info['reason'] = self.legality(shot)
        if self.shot_info['is_legal']:
            self.log.add_msg("The shot was legal.", quiet=True)
        else:
            self.log.add_msg(f"Illegal shot! {self.shot_info['reason']}", sentiment='bad')
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
            self.log.add_msg(f"{player.name} points: {player.points}", quiet=True)

        if self.is_game_over(shot):
            self.game_over = True
            self.decide_winner(shot)
            self.log.add_msg(f"Game over! {self.winner.name} wins!", sentiment='good')
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















