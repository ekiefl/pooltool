#! /usr/bin/env python

import pooltool
import pooltool.events as e

from pooltool.objects import DummyBall

import uuid

from abc import ABC, abstractmethod


class Game(ABC):
    def __init__(self):
        self.players = None
        self.shot_number = None
        self.turn_number = None
        self.last_player = None
        self.active_player = None


    def create_players(self, num_players):
        self.players = []
        for _ in range(num_players):
            self.players.append(Player())


    def init(self, num_players):
        self.create_players(num_players)
        self.shot_number = 0
        self.turn_number = 0
        self.set_next_player()


    def set_next_player(self):
        self.last_player, self.active_player = self.active_player, self.players[self.turn_number % len(self.players)]
        if self.last_player:
            self.last_player.is_shooting = False
        self.active_player.is_shooting = True


    def process_shot(self, shot):
        self.is_legal(shot)


    def advance(self):
        self.turn_number += 1
        self.shot_number += 1

        self.set_next_player()


    @abstractmethod
    def is_legal(self, shot):
        pass


class NineBall(Game):
    def __init__(self):
        Game.__init__(self)


    def get_lowest_ball(self, shot):
        lowest = DummyBall()
        lowest.id = '10'

        for ball in shot.balls.values():
            if ball.id == 'cue':
                continue
            if ball.history.s[0] == pooltool.pocketed:
                continue
            if int(ball.id) < int(lowest.id):
                lowest = ball

        return lowest


    def is_lowest_hit_first(self, shot):
        lowest = self.get_lowest_ball(shot)
        cue = shot.balls['cue']

        collisions = cue.filter_events_by_type(e.type_ball_ball)

        return True if (collisions.num_events > 0 and lowest in collisions.get(0).agents) else False


    def is_legal_break(self, shot):
        if self.shot_number != 0:
            return True

        ball_pocketed = True if shot.filter_events_by_type(e.type_ball_pocket).num_events > 0 else False
        enough_cushions = True if len(self.numbered_balls_that_hit_cushion(shot)) >= 4 else False

        return True if (ball_pocketed or enough_cushions) else False


    def numbered_balls_that_hit_cushion(self, shot):
        numbered_balls = [ball for ball in shot.balls.values() if ball.id != 'cue']

        cushion_events = shot.\
            filter_events_by_type(e.type_ball_cushion).\
            filter_events_by_ball_id(numbered_balls)

        return set([event.agents[0].id for event in cushion_events.events])


    def is_cue_pocketed(self, shot):
        return True if shot.balls['cue'].s == pooltool.pocketed else False


    def is_cushion_after_first_contact(self, shot):
        if not self.is_lowest_hit_first(shot):
            return False

        first_contact = shot.balls['cue'].filter_events_by_type(e.type_ball_ball).get(0)
        cushion_events = shot.\
            filter_events_by_time(first_contact.time).\
            filter_events_by_type(e.type_ball_cushion)

        return True if cushion_events.num_events > 0 else False


    def is_legal(self, shot):
        reason = None

        if not self.is_lowest_hit_first(shot):
            reason = 'Lowest ball not hit first'
        elif not self.is_cushion_after_first_contact(shot):
            reason = 'Cushion not contacted after first contact'
        elif self.is_cue_on_table(shot):
            reason = 'Cue ball in pocket!'
        elif not self.is_legal_break(shot):
            reason = 'Must contact 4 rails or pot 1 ball'

        return (True, reason) if not reason else (False, reason)



class Player(object):
    def __init__(self):
        self.id = uuid.uuid4().hex
        self.name = None
        self.is_shooting = False


    def set_name(self, name):
        self.name = name


