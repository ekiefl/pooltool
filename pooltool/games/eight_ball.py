#! /usr/bin/env python

import pooltool
import pooltool.ani as ani
import pooltool.events as e
import pooltool.ani.utils as autils

from pooltool.games import Player, Game
from pooltool.objects import DummyBall
from pooltool.layouts import EightBallRack

from panda3d.core import *
from direct.interval.IntervalGlobal import *
from direct.gui.OnscreenText import OnscreenText


class EightBall(Game):
    def __init__(self, apa_rules=False):
        self.is_call_ball = True
        self.is_call_pocket = True
        Game.__init__(self)
        self.create_players(2)

        self.solids = [str(i) for i in range(1,8)]
        self.stripes = [str(i) for i in range(9,16)]

        # Allow stroke mode during break
        self.ball_call = 'dummy'
        self.pocket_call = 'dummy'

        for player in self.players:
            player.stripes_or_solids = None
            player.target_balls = []
            player.can_cue = ['cue']


    def start(self):
        self.active_player.ball_in_hand = ['cue']


    def setup_initial_layout(self, table, ball_kwargs={}):
        self.layout = EightBallRack(ordered=True, **ball_kwargs)
        self.layout.center_by_table(table)

        # get the cueing ball
        self.layout.get_balls_dict()


    def set_initial_cueing_ball(self, balls):
        return balls['cue']


    def award_points(self, shot):
        self.shot_info['points'] = {player: 0 for player in self.players}


    def decide_winner(self, shot):
        if self.shot_info['is_legal']:
            self.winner = self.active_player
        else:
            self.winner = self.players[0] if self.players[0] != self.active_player else self.players[1]


    def award_ball_in_hand(self, shot):
        if not self.shot_info['is_legal']:
            self.shot_info['ball_in_hand'] = ['cue']
            self.respot(shot, 'cue', shot.table.w/2, shot.table.l*1/4, shot.balls['cue'].R)
        else:
            self.shot_info['ball_in_hand'] = None


    def respot_balls(self, shot):
        pass


    def is_turn_over(self, shot):
        if not self.shot_info['is_legal']:
            return True

        pocket_events = shot.filter_type(e.type_ball_pocket)

        if self.active_player.stripes_or_solids is None and pocket_events.num_events > 0:
            return False

        for event in pocket_events.events:
            ball, pocket = event.agents
            if ball == self.ball_call and pocket == self.pocket_call:
                self.log.add_msg(f"Ball potted: {ball.id}", sentiment='good')
                return False

        return True


    def is_game_over(self, shot):
        pocket_events = shot.filter_type(e.type_ball_pocket)
        for event in pocket_events.events:
            if '8' in (event.agents[0].id, event.agents[1].id):
                return True


    def is_object_ball_hit_first(self, shot):
        cue = shot.balls['cue']
        collisions = cue.filter_type(e.type_ball_ball)
        if collisions.num_events == 0:
            return False

        first_collision = collisions.get(0)
        ball1, ball2 = first_collision.agents
        first_ball_hit = ball1 if ball1.id != 'cue' else ball2

        if self.active_player.stripes_or_solids is None:
            # stripes or solids not yet determined
            return True

        if first_ball_hit.id in self.active_player.target_balls:
            return True

        return False


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
        if not self.is_object_ball_hit_first(shot):
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


    def is_cue_ball_strike(self, shot):
        cue_strike = shot.filter_type(e.type_stick_ball)
        if cue_strike.get(0).agents[1].id == 'cue':
            return True
        else:
            return False


    def is_8_ball_sunk_before_others(self, shot):
        if '8' in self.active_player.target_balls:
            return False

        pocket_events = shot.filter_type(e.type_ball_pocket)
        for event in pocket_events.events:
            if '8' in (event.agents[0].id, event.agents[1].id):
                return True


    def legality(self, shot):
        """Returns whether or not a shot is legal, and the reason"""
        reason = None

        if self.is_8_ball_sunk_before_others(shot):
            reason = '8-ball sunk before others!'
        elif not self.is_cue_ball_strike(shot):
            reason = 'Wrong ball was cued'
        elif not self.is_object_ball_hit_first(shot):
            reason = 'Object ball not hit first'
        elif not self.is_shot_called(shot):
            reason = 'No shot called!'
        elif self.is_cue_pocketed(shot):
            reason = 'Cue ball in pocket!'
        elif not self.is_cushion_after_first_contact(shot):
            reason = 'Cushion not contacted after first contact'
        elif not self.is_legal_break(shot):
            reason = 'Must contact 4 rails or pot 1 ball'

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

            states = [ball.s for ball in shot.balls.values() if ball.id in player.target_balls]
            if all([state == pooltool.pocketed for state in states]):
                player.target_balls.append('8')


    def decide_stripes_or_solids(self, shot):
        is_open = True if self.active_player.stripes_or_solids is None else False
        player_potted = not self.shot_info['is_turn_over']
        is_break_shot = self.shot_number == 0

        if (not is_open) or (not player_potted) or (is_break_shot):
            return

        if self.ball_call.id in self.stripes:
            self.active_player.stripes_or_solids = 'stripes'
            self.active_player.target_balls = self.stripes
            other_player = self.players[0] if self.players[0] != self.active_player else self.players[1]
            other_player.stripes_or_solids = 'solids'
            other_player.target_balls = self.solids
        else:
            self.active_player.stripes_or_solids = 'solids'
            self.active_player.target_balls = self.solids
            other_player = self.players[0] if self.players[0] != self.active_player else self.players[1]
            other_player.stripes_or_solids = 'stripes'
            other_player.target_balls = self.stripes

        self.log.add_msg(f"{self.active_player.name} takes {self.active_player.stripes_or_solids}", sentiment='good')


