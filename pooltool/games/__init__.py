#! /usr/bin/env python

import uuid

from abc import ABC, abstractmethod


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


    def create_players(self, num_players):
        self.players = []
        for _ in range(num_players):
            self.players.append(Player())


    def init(self, num_players):
        self.create_players(num_players)
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
            print(f"Player {self.active_player.id[:5]} is up")
            self.active_player.is_shooting = True
            if self.last_player:
                self.last_player.is_shooting = False


    def process_shot(self, shot):
        self.shot_info = {}
        self.shot_info['is_legal'], self.shot_info['reason'] = self.legality(shot)
        if self.shot_info['is_legal']:
            print(f"The shot was legal.")
        else:
            print(f"The shot was illegal! {self.shot_info['reason']}")
        self.shot_info['is_turn_over'] = self.is_turn_over(shot)

        self.award_points(shot)
        self.award_ball_in_hand(shot)
        self.respot_balls(shot)


    def respot(self, shot, ball_id, x, y, z):
        """Move cue ball to head spot or close to"""
        R = shot.balls[ball_id].R
        shot.balls[ball_id].rvw[0] = [x, y, z]


    def advance(self, shot):
        for player in self.players:
            player.points += self.shot_info['points'][player]
            print(f"Player {player.id[:5]} points: {player.points}")

        if self.is_game_over(shot):
            self.game_over = True
            self.decide_winner(shot)
            print(f"Game over! The winner was {self.winner.id[:5]}")
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


