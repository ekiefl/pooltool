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
        print("---------------------------")
        print([ball.id for ball in shot.balls.values()])
        print(ball_id)
        print(ball_id in [ball.id for ball in shot.balls.values()])
        print(ball_id in [ball.id for ball in shot.balls.values()])
        print("---------------------------")
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


class NineBall(Game):
    def __init__(self, apa_rules=False):
        Game.__init__(self)
        self.apa_rules = apa_rules


    def award_points(self, shot):
        """APA-style points"""
        self.shot_info['points'] = {player: 0 for player in self.players}

        if not self.shot_info['is_legal']:
            return

        points = 0
        for event in shot.filter_type(e.type_ball_pocket).events:
            ball, pocket = event.agents
            points += 2 if (ball.id == '9') else 1

        self.shot_info['points'][self.active_player] = points


    def decide_winner(self, shot):
        if self.apa_rules:
            if self.players[0].points == self.players[1].points:
                self.winner = None
                self.tie = True
            else:
                self.winner = max(self.players, key = lambda x: x.points)
        else:
            self.winner = self.active_player


    def award_ball_in_hand(self, shot):
        if not self.shot_info['is_legal']:
            self.ball_in_hand = 'cue'
            self.respot(shot, self.ball_in_hand, shot.table.w/2, shot.table.l*1/4, shot.balls[self.ball_in_hand].R)
        else:
            self.ball_in_hand = None


    def respot_balls(self, shot):
        highest = self.get_highest_ball(shot)
        lowest = self.get_lowest_ball(shot)
        cue_ball = shot.balls['cue']

        pocket_events = shot.filter_type(e.type_ball_pocket)
        pocketed_balls = [event.agents[0] for event in pocket_events.events]

        #if (highest == lowest) and (highest in pocketed_balls) and (cue_ball in pocketed_balls):
        if (highest in pocketed_balls):
            self.respot(shot, highest.id, shot.table.w/2, shot.table.l*3/4, highest.R)


    def is_turn_over(self, shot):
        if not self.shot_info['is_legal']:
            return True

        if shot.filter_type(e.type_ball_pocket).num_events > 0:
            print(f"{shot.filter_type(e.type_ball_pocket).num_events} balls potted for player {self.active_player.id[:5]}")
            return False

        return True


    def is_game_over(self, shot):
        highest = self.get_highest_ball(shot)

        pocket_events = shot.filter_type(e.type_ball_pocket)
        pocketed_balls = [event.agents[0] for event in pocket_events.events]

        if highest in pocketed_balls and self.shot_info['is_legal']:
            return True
        else:
            return False


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


    def get_highest_ball(self, shot):
        highest = DummyBall()
        highest.id = '0'

        for ball in shot.balls.values():
            if ball.id == 'cue':
                continue
            if ball.history.s[0] == pooltool.pocketed:
                continue
            if int(ball.id) > int(highest.id):
                highest = ball

        return highest


    def is_lowest_hit_first(self, shot):
        lowest = self.get_lowest_ball(shot)
        cue = shot.balls['cue']

        collisions = cue.filter_type(e.type_ball_ball)

        return True if (collisions.num_events > 0 and lowest in collisions.get(0).agents) else False


    def is_legal_break(self, shot):
        if self.shot_number != 0:
            return True

        ball_pocketed = True if shot.filter_type(e.type_ball_pocket).num_events > 0 else False
        enough_cushions = True if len(self.numbered_balls_that_hit_cushion(shot)) >= 4 else False

        return True if (ball_pocketed or enough_cushions) else False


    def numbered_balls_that_hit_cushion(self, shot):
        numbered_balls = [ball for ball in shot.balls.values() if ball.id != 'cue']

        cushion_events = shot.\
            filter_type(e.type_ball_cushion).\
            filter_ball(numbered_balls)

        return set([event.agents[0].id for event in cushion_events.events])


    def is_cue_pocketed(self, shot):
        return True if shot.balls['cue'].s == pooltool.pocketed else False


    def is_cushion_after_first_contact(self, shot):
        if not self.is_lowest_hit_first(shot):
            return False

        first_contact = shot.balls['cue'].filter_type(e.type_ball_ball).get(0)
        cushion_events = shot.\
            filter_time(first_contact.time).\
            filter_type(e.type_ball_cushion)

        cushion_hit = True if cushion_events.num_events > 0 else False

        numbered_balls = [ball for ball in shot.balls.values() if ball.id != 'cue']
        ball_pocketed = shot.\
            filter_type(e.type_ball_pocket).\
            filter_ball(numbered_balls).\
            num_events > 0

        return True if (cushion_hit or ball_pocketed) else False


    def legality(self, shot):
        """Returns whether or not a shot is legal, and the reason"""
        reason = None

        if not self.is_lowest_hit_first(shot):
            reason = 'Lowest ball not hit first'
        elif self.is_cue_pocketed(shot):
            reason = 'Cue ball in pocket!'
        elif not self.is_cushion_after_first_contact(shot):
            reason = 'Cushion not contacted after first contact'
        elif not self.is_legal_break(shot):
            reason = 'Must contact 4 rails or pot 1 ball'

        return (True, reason) if not reason else (False, reason)



class Player(object):
    def __init__(self):
        self.id = uuid.uuid4().hex
        self.name = None
        self.is_shooting = False
        self.points = 0


    def set_name(self, name):
        self.name = name


