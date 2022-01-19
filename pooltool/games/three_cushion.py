#! /usr/bin/env python

import pooltool.events as e
import pooltool.constants as c

from pooltool.games import Player, Game
from pooltool.layouts import ThreeCushionRack


class ThreeCushion(Game):
    def __init__(self):
        self.points_to_win = 20
        self.is_call_ball = False
        self.is_call_pocket = False
        Game.__init__(self)
        self.create_players(2)


    def start(self):
        self.players[0].can_cue = ['white']
        self.players[0].target_balls = ['yellow', 'red']
        self.players[1].can_cue = ['yellow']
        self.players[1].target_balls = ['white', 'red']


    def setup_initial_layout(self, table, ball_kwargs={}):
        self.balls = ThreeCushionRack(table=table, **ball_kwargs).balls


    def set_initial_cueing_ball(self, balls):
        return balls['white']


    def award_points(self, shot):
        self.shot_info['points'] = {player: 0 for player in self.players}

        if not self.shot_info['is_legal']:
            return

        if self.is_hit(shot):
            self.shot_info['points'][self.active_player] = 1


    def decide_winner(self, shot):
        self.winner = self.active_player


    def award_ball_in_hand(self, shot):
        self.shot_info['ball_in_hand'] = None


    def respot_balls(self, shot):
        pass


    def is_turn_over(self, shot):
        if not self.shot_info['is_legal']:
            return True

        if self.is_hit(shot):
            return False

        return True


    def is_game_over(self, shot):
        for player in self.players:
            if player.points == self.points_to_win:
                return True
        return False


    def legality(self, shot):
        """Returns whether or not a shot is legal, and the reason"""
        return (True, None)


    def is_hit(self, shot):
        # This is the ball the player hit
        cue = self.active_player.can_cue[0]

        get_other_agent = lambda event: event.agents[0].id if event.agents[0].id != cue else event.agents[1].id
        get_agent_ids = lambda event: [agent.id for agent in event.agents]

        first_hit = False
        second_hit = False
        cushion_count = 0
        for event in shot.events:
            if event.event_type == 'ball-cushion' and event.agents[0].id == cue:
                cushion_count += 1

            if not first_hit and event.event_type == 'ball-ball':
                first_hit_agent = get_other_agent(event)
                first_hit = True
                continue

            if not second_hit and event.event_type == 'ball-ball':
                agents = get_agent_ids(event)
                if cue not in agents:
                    pass
                elif get_other_agent(event) == first_hit_agent:
                    pass
                else:
                    second_hit_agent = get_other_agent(event)
                    second_hit = True
                    break
        else:
            return False

        if cushion_count < 3:
            return False

        return True


    def advance(self, shot):
        super().advance(shot)


