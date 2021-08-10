#! /usr/bin/env python

import pooltool
import pooltool.events as e

from pooltool.games import Player, Game
from pooltool.objects import DummyBall
from pooltool.layouts import NineBallRack


class NineBall(Game):
    def __init__(self, apa_rules=False):
        self.is_call_ball = False
        self.is_call_pocket = False
        Game.__init__(self)
        self.apa_rules = apa_rules
        self.create_players(2)


    def start(self):
        self.active_player.ball_in_hand = ['cue']


    def setup_initial_layout(self, table, ball_kwargs={}):
        self.layout = NineBallRack(ordered=True, **ball_kwargs)
        self.layout.center_by_table(table)

        # get the cueing ball
        self.layout.get_balls_dict()


    def set_initial_cueing_ball(self, balls):
        return balls['cue']


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
            self.shot_info['ball_in_hand'] = ['cue']
            self.respot(shot, 'cue', shot.table.w/2, shot.table.l*1/4, shot.balls['cue'].R)
        else:
            self.shot_info['ball_in_hand'] = None


    def respot_balls(self, shot):
        highest = self.get_highest_ball(shot)
        lowest = self.get_lowest_ball(shot)

        pocket_events = shot.filter_type(e.type_ball_pocket)
        pocketed_balls = [event.agents[0] for event in pocket_events.events]

        if (highest == lowest) and (highest in pocketed_balls) and not self.shot_info['is_legal']:
            self.respot(shot, highest.id, shot.table.w/2, shot.table.l*3/4, highest.R)


    def is_turn_over(self, shot):
        if not self.shot_info['is_legal']:
            return True

        pocket_events = shot.filter_type(e.type_ball_pocket)
        if pocket_events.num_events > 0:
            balls_potted = [e.agents[0].id for e in pocket_events.events]
            self.log.add_msg(f"Ball(s) potted: {','.join(balls_potted)}", sentiment='good')
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
        lowest = DummyBall(ball_id='10')

        for ball in shot.balls.values():
            if ball.id == 'cue':
                continue
            if ball.history.s[0] == pooltool.pocketed:
                continue
            if int(ball.id) < int(lowest.id):
                lowest = ball

        return lowest


    def get_highest_ball(self, shot):
        highest = DummyBall(ball_id='0')

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


    def is_cue_ball_strike(self, shot):
        cue_strike = shot.filter_type(e.type_stick_ball)
        if cue_strike.get(0).agents[1].id == 'cue':
            return True
        else:
            return False


    def legality(self, shot):
        """Returns whether or not a shot is legal, and the reason"""
        reason = None

        if not self.is_cue_ball_strike(shot):
            reason = 'Wrong ball was cued'
        elif not self.is_lowest_hit_first(shot):
            reason = 'Lowest ball not hit first'
        elif self.is_cue_pocketed(shot):
            reason = 'Cue ball in pocket!'
        elif not self.is_cushion_after_first_contact(shot):
            reason = 'Cushion not contacted after first contact'
        elif not self.is_legal_break(shot):
            reason = 'Must contact 4 rails or pot 1 ball'

        return (True, reason) if not reason else (False, reason)



